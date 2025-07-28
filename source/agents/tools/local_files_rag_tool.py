# Python 3.12
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, ConfigDict

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.tools import Tool

from langchain_community.document_loaders.directory import DirectoryLoader
from langchain_community.document_loaders.text import TextLoader
from langchain_community.document_loaders.unstructured import UnstructuredFileLoader
from langchain_community.document_loaders.csv_loader import CSVLoader

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS

from source.dev_logger import debug
from source.global_models import cached_embeddings, default_cheapest_model
from source.locations_and_config import uploads_dir


class SourceRef(BaseModel):
    id: int
    metadata: dict[str, Any] = Field(default_factory=dict)


class RAGAnswer(BaseModel):
    answer: str
    sources: list[SourceRef]


class LocalFilesRAGTool(BaseModel):
    """
    Async RAG over a local directory (pdf/docx/xlsx/csv/pptx/txt, etc.).

    - index(): build/persist FAISS
    - answer(): retrieve+generate with citations
    - __call__(): convenience awaitable
    - as_tool(): LangChain Tool wrapper
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    data_dir: Path = Field(..., description="Directory with source documents")
    index_dir: Path = Field(default=Path(".rag_index/faiss"))
    chunk_size: int = 1000
    chunk_overlap: int = 200
    llm_model: str = "gpt-4o-mini"
    embeddings: Embeddings | None = None
    allow_unsafe_deser: bool = True

    _vs: FAISS | None = None

    async def index(self) -> None:
        """
        Build and persist a FAISS index from .txt, .pdf, and .csv files.
        """
        # Log all files for debug
        files = list(self.data_dir.rglob("*"))
        debug("All files under %s: %s", self.data_dir, files)
        if not files:
            raise FileNotFoundError(f"No files found under: {self.data_dir!r}")

        # 1) Load .txt via TextLoader
        loader_txt = DirectoryLoader(
            str(self.data_dir),
            glob="**/*.txt",
            loader_cls=TextLoader,
            recursive=True,
            show_progress=True,
            silent_errors=True,
        )
        docs_txt: list[Document] = await asyncio.to_thread(loader_txt.load)

        # 2) Load .pdf via UnstructuredFileLoader
        loader_pdf = DirectoryLoader(
            str(self.data_dir),
            glob="**/*.pdf",
            loader_cls=UnstructuredFileLoader,
            recursive=True,
            show_progress=True,
            silent_errors=True,
        )
        docs_pdf: list[Document] = await asyncio.to_thread(loader_pdf.load)

        # 3) Load .csv via CSVLoader
        loader_csv = DirectoryLoader(
            str(self.data_dir),
            glob="**/*.csv",
            loader_cls=CSVLoader,
            recursive=True,
            show_progress=True,
            silent_errors=True,
        )
        docs_csv: list[Document] = await asyncio.to_thread(loader_csv.load)

        docs = docs_txt + docs_pdf + docs_csv
        if not docs:
            raise FileNotFoundError(
                f"Found {len(files)} file(s) under {self.data_dir!r} "
                "but none could be loaded. Check loader dependencies!"
            )

        # Split and index
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
        )
        chunks: list[Document] = await asyncio.to_thread(splitter.split_documents, docs)

        vs = await FAISS.afrom_documents(chunks, self.embeddings or cached_embeddings)
        self.index_dir.mkdir(parents=True, exist_ok=True)
        await asyncio.to_thread(vs.save_local, str(self.index_dir), index_name="index")
        self._vs = vs
        debug("Built FAISS index with %d chunks from %d docs.", len(chunks), len(docs))

    async def _ensure_vs(self) -> FAISS:
        """Load or rebuild the FAISS index."""
        if self._vs:
            return self._vs

        try:
            self._vs = await asyncio.to_thread(
                FAISS.load_local,
                str(self.index_dir),
                self.embeddings or cached_embeddings,
                index_name="index",
                allow_dangerous_deserialization=self.allow_unsafe_deser,
            )
            debug("Loaded FAISS index from %s", self.index_dir)
        except (FileNotFoundError, ValueError, RuntimeError) as e:
            debug("Index load failed (%s), rebuilding…", e)
            await self.index()
        assert self._vs is not None
        return self._vs

    async def answer(self, question: str, k: int = 4) -> dict[str, Any]:
        vs = await self._ensure_vs()
        retriever = vs.as_retriever(search_kwargs={"k": k})
        retrieved = await retriever.ainvoke(question)

        blocks: list[str] = []
        for i, d in enumerate(retrieved, start=1):
            meta = d.metadata or {}
            src = meta.get("source") or meta.get("filename") or "unknown"
            page = meta.get("page") or meta.get("page_number")
            tag = f"[{i}] {src}" + (f":p{page}" if page is not None else "")
            blocks.append(f"{tag}\n{d.page_content.strip()}")

        context = "\n\n---\n\n".join(blocks) or "No context retrieved."
        system_prompt = (
            "You are a precise RAG assistant. Answer only from the context. "
            "If the answer isn't in the context, say you don't know. "
            "Cite sources like [1], [2] at the end."
        )
        user_msg = f"Question: {question}\n\nContext:\n{context}"
        msg = await default_cheapest_model.ainvoke([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_msg},
        ])

        answer = getattr(msg, "content", str(msg)).strip()
        sources = [{"id": idx + 1, "metadata": d.metadata or {}} for idx, d in enumerate(retrieved)]
        return {"answer": answer, "sources": sources}

    async def __call__(self, question: str, k: int = 4) -> str:
        return (await self.answer(question, k=k))["answer"]

    def as_tool(self) -> Tool:
        async def _run(question: str, k: int = 4) -> str:
            return await self(question, k=k)

        return Tool(
            name="local_rag_search_async",
            description=(
                "Async search & answer over local documents "
                "(PDF/DOCX/XLSX/CSV/TXT/PPTX). Returns answer with citations."
            ),
            func=None,
            coroutine=_run,
        )


# -----------------------------
# Example usage
# -----------------------------
async def main() -> None:
    rag = LocalFilesRAGTool(
        data_dir=uploads_dir,
        index_dir=uploads_dir / ".rag_index/faiss",
        embeddings=cached_embeddings,           # optional; can be omitted
        allow_unsafe_deser=True,                # explicitly opt-in for local, trusted index
    )

    # Build the index if missing; otherwise it will lazy-load.
    # You can uncomment to force a rebuild:
    # await rag.index()

    resp = await rag.answer("what were the earnings?", k=6)
    debug(resp["answer"])


if __name__ == "__main__":
    asyncio.run(main())
