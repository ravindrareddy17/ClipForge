# CSE473 LLM & Generative AI — Recognition of Prior Learning (RPL) Curriculum Mapping

This document provides an exhaustive, itemized mapping of the **40 core curriculum topics** of the CSE473 syllabus against the concrete implementation of **ClipForge AI V2**. Every topic is evaluated with its status (**IMPLEMENTED**, **PARTIALLY IMPLEMENTED**, **EXPERIMENTAL**, or **NOT APPLICABLE**) along with exact file and line references.

---

## Unit I: LLM Foundations, Attention & Transformer Architectures

| # | Topic | Status | Implementation Details & File Reference |
| :--- | :--- | :--- | :--- |
| **1** | **Tokenization & Subword Splitting** | **IMPLEMENTED** | Interactive subword visualizer decomposing text into discrete tokens and token IDs. [`cse473_lab.py:27-56`](file:///e:/ai%20forge/backend/clipforge_engine/cse473_lab.py#L27-L56). |
| **2** | **Vocabulary Index Mapping & Token IDs** | **IMPLEMENTED** | Hash-mapped vocabulary index generator mapping characters and tokens to discrete IDs. [`cse473_lab.py:35-48`](file:///e:/ai%20forge/backend/clipforge_engine/cse473_lab.py#L35-L48). |
| **3** | **Embedding Lookup Layers** | **IMPLEMENTED** | Real non-zero 768-dim embedding lookup with dynamic dimension health check. [`rag.py:49-94`](file:///e:/ai%20forge/backend/clipforge_engine/rag.py#L49-L94). |
| **4** | **Positional Encoding (Sinusoidal)** | **IMPLEMENTED** | Exact sinusoidal positional encoding matrix implementation $\sin(pos/10000^{2i/d})$. [`cse473_lab.py:100-112`](file:///e:/ai%20forge/backend/clipforge_engine/cse473_lab.py#L100-L112). |
| **5** | **Scaled Dot-Product Self-Attention** | **IMPLEMENTED** | $\text{Softmax}(QK^T / \sqrt{d_k})$ matrix calculation with query/key products. [`cse473_lab.py:59-90`](file:///e:/ai%20forge/backend/clipforge_engine/cse473_lab.py#L59-L90). |
| **6** | **Multi-Head Attention Formulations** | **IMPLEMENTED** | Multi-head attention matrix visualizer generating independent heads. [`cse473_lab.py:68-87`](file:///e:/ai%20forge/backend/clipforge_engine/cse473_lab.py#L68-L87). |
| **7** | **Transformer Block Forward Pass** | **IMPLEMENTED** | Full block trace: Tokenization $\to$ Embedding $\to$ PE $\to$ MHA $\to$ Add&Norm $\to$ FFN $\to$ Norm. [`cse473_lab.py:93-138`](file:///e:/ai%20forge/backend/clipforge_engine/cse473_lab.py#L93-L138). |
| **8** | **Causal Masking in Decoders** | **PARTIALLY IMPLEMENTED**| Causal generation in local Ollama inference (`qwen2.5:3b`); forward simulator uses bidirectional self-attention. |
| **9** | **Encoder-Decoder Cross-Attention** | **EXPERIMENTAL** | Cross-modal audio-to-text attention performed within OpenAI Whisper backend. |
| **10**| **Feed-Forward Networks (FFN & GELU)** | **IMPLEMENTED** | FFN layer simulation with non-linear activation and residual connections. [`cse473_lab.py:118-124`](file:///e:/ai%20forge/backend/clipforge_engine/cse473_lab.py#L118-L124). |

---

## Unit II: Prompt Engineering, Agents & Tool Calling

| # | Topic | Status | Implementation Details & File Reference |
| :--- | :--- | :--- | :--- |
| **11**| **Zero-Shot Prompting** | **IMPLEMENTED** | Multi-paradigm comparator zero-shot baseline prompt. [`cse473_lab.py:157-160`](file:///e:/ai%20forge/backend/clipforge_engine/cse473_lab.py#L157-L160). |
| **12**| **Few-Shot In-Context Learning** | **IMPLEMENTED** | Multi-paradigm comparator with in-context Q&A examples. [`cse473_lab.py:161-170`](file:///e:/ai%20forge/backend/clipforge_engine/cse473_lab.py#L161-L170). |
| **13**| **Chain-of-Thought (CoT)** | **IMPLEMENTED** | Multi-paradigm step-by-step reasoning prompt comparator. [`cse473_lab.py:195-198`](file:///e:/ai%20forge/backend/clipforge_engine/cse473_lab.py#L195-L198). |
| **14**| **Role-Based / Persona Prompting** | **IMPLEMENTED** | Senior astrophysicist persona demonstration in prompt studio. [`cse473_lab.py:179-182`](file:///e:/ai%20forge/backend/clipforge_engine/cse473_lab.py#L179-L182). |
| **15**| **Structured Output (JSON Schema)** | **IMPLEMENTED** | Strict JSON schema format enforcement in summary and prompt comparator. [`agents.py:37-71`](file:///e:/ai%20forge/backend/clipforge_engine/agents.py#L37-L71), [`cse473_lab.py:171-178`](file:///e:/ai%20forge/backend/clipforge_engine/cse473_lab.py#L171-L178). |
| **16**| **ReAct Framework (Reasoning + Acting)** | **IMPLEMENTED** | 3-iteration bounded ReAct loop executing Plan $\to$ Tool $\to$ Verify $\to$ Synthesize. [`video_qa_agents.py:365-440`](file:///e:/ai%20forge/backend/clipforge_engine/video_qa_agents.py#L365-L440). |
| **17**| **Function Calling & Tool Selection** | **IMPLEMENTED** | Tool registry and JSON schema argument validation engine. [`cse473_lab.py:223-280`](file:///e:/ai%20forge/backend/clipforge_engine/cse473_lab.py#L223-L280). |
| **18**| **Multi-Agent Architecture** | **IMPLEMENTED** | 6 specialized agent personas (`QueryPlanner`, `Retrieval`, `Timeline`, `Evidence`, `Synthesis`, `Guardrail`). [`video_qa_agents.py:145-360`](file:///e:/ai%20forge/backend/clipforge_engine/video_qa_agents.py#L145-L360). |
| **19**| **Grounded In-Context Prompting** | **IMPLEMENTED** | System-prompt grounding enforcing timestamp citations and zero-hallucination. [`rag.py:574-670`](file:///e:/ai%20forge/backend/clipforge_engine/rag.py#L574-L670). |
| **20**| **Conversational Memory Persistence** | **IMPLEMENTED** | Relational chat history filtered by workspace and video ID. [`db.py:835-865`](file:///e:/ai%20forge/backend/clipforge_engine/db.py#L835-L865). |

---

## Unit III: Fine-Tuning, Parameter Efficiency & Adaptation

| # | Topic | Status | Implementation Details & File Reference |
| :--- | :--- | :--- | :--- |
| **21**| **Full Parameter Fine-Tuning** | **NOT APPLICABLE**| ClipForge deploys local inference engines without full-weight re-training. Parameter comparison simulated in [`cse473_lab.py:293`](file:///e:/ai%20forge/backend/clipforge_engine/cse473_lab.py#L293). |
| **22**| **Parameter-Efficient Fine-Tuning (PEFT)** | **IMPLEMENTED** | Parameter efficiency calculator evaluating parameter counts and memory savings. [`cse473_lab.py:285-322`](file:///e:/ai%20forge/backend/clipforge_engine/cse473_lab.py#L285-L322). |
| **23**| **Low-Rank Adaptation (LoRA)** | **IMPLEMENTED** | $W = W_0 + B \cdot A$ matrix decomposition demonstration with dimension analysis and forward pass. [`cse473_lab.py:285-367`](file:///e:/ai%20forge/backend/clipforge_engine/cse473_lab.py#L285-L367). |
| **24**| **Quantized LoRA (QLoRA)** | **EXPERIMENTAL** | Quantization + LoRA memory trade-off model in studio. |
| **25**| **Prompt Tuning / Soft Prompts** | **EXPERIMENTAL** | Vectorized prefix embedding injection simulated in lab. |
| **26**| **Post-Training Quantization (INT4 / GGUF)** | **IMPLEMENTED** | Memory footprint and latency benchmark across FP32, FP16, INT8, and INT4 (Q4_K_M). [`cse473_lab.py:370-410`](file:///e:/ai%20forge/backend/clipforge_engine/cse473_lab.py#L370-L410). |
| **27**| **Direct Preference Optimization (DPO)** | **EXPERIMENTAL** | Pairwise virality scoring algorithm comparing hook alternatives. [`pipeline.py:480-520`](file:///e:/ai%20forge/backend/clipforge_engine/pipeline.py#L480-L520). |
| **28**| **RLHF Principles** | **EXPERIMENTAL** | User accept/reject buttons for rendered clips in UI update internal virality scores. |
| **29**| **Q-Learning & Bellman Equation** | **IMPLEMENTED** | Full tabular Q-learning simulation in GridWorld with epsilon-greedy policy and Bellman updates. [`cse473_lab.py:413-488`](file:///e:/ai%20forge/backend/clipforge_engine/cse473_lab.py#L413-L488). |
| **30**| **Reward Modeling & Policy Derivation** | **IMPLEMENTED** | Reward shaping (Goal +10, Pit -10, Step -0.1) and optimal policy matrix extraction. [`cse473_lab.py:440-480`](file:///e:/ai%20forge/backend/clipforge_engine/cse473_lab.py#L440-L480). |

---

## Unit VI: RAG, Evaluation, Security & Deployment

| # | Topic | Status | Implementation Details & File Reference |
| :--- | :--- | :--- | :--- |
| **31**| **Segment-Aware Overlapping Chunking** | **IMPLEMENTED** | 120–180 words, 15–20% overlap, respecting Whisper word bounds with deterministic IDs. [`rag.py:95-175`](file:///e:/ai%20forge/backend/clipforge_engine/rag.py#L95-L175). |
| **32**| **Dense Vector Embeddings (ChromaDB)** | **IMPLEMENTED** | ChromaDB collections indexed with genuine 768-dim `nomic-embed-text` vectors. [`rag.py:200-245`](file:///e:/ai%20forge/backend/clipforge_engine/rag.py#L200-L245). |
| **33**| **Lexical Search (BM25)** | **IMPLEMENTED** | Token-weighted BM25 keyword matching with length normalization across full video transcripts. [`rag.py:270-334`](file:///e:/ai%20forge/backend/clipforge_engine/rag.py#L270-L334). |
| **34**| **Hybrid Search & RRF Fusion** | **IMPLEMENTED** | Reciprocal Rank Fusion merging BM25 and vector rank lists without calibration skew. [`rag.py:390-480`](file:///e:/ai%20forge/backend/clipforge_engine/rag.py#L390-L480). |
| **35**| **Context Expansion & Re-ranking** | **IMPLEMENTED** | Chronological window expansion ($\pm 1$ neighbor chunks) for narrative continuity. [`rag.py:518-565`](file:///e:/ai%20forge/backend/clipforge_engine/rag.py#L518-L565). |
| **36**| **RAG Evaluation & Precision@K** | **IMPLEMENTED** | Automated 20-question evaluation benchmark runner calculating accuracy and latency. [`cse473_lab.py:530-610`](file:///e:/ai%20forge/backend/clipforge_engine/cse473_lab.py#L530-L610). |
| **37**| **Hallucination Suppression** | **IMPLEMENTED** | Zero-hallucination negative controls returning standardized refusal for out-of-domain queries. [`video_qa_agents.py:345-360`](file:///e:/ai%20forge/backend/clipforge_engine/video_qa_agents.py#L345-L360). |
| **38**| **Prompt Injection Sandboxing** | **IMPLEMENTED** | Semantic isolation inside `<video_transcript_data>` tags and automated injection testing suite. [`rag.py:602-612`](file:///e:/ai%20forge/backend/clipforge_engine/rag.py#L602-L612), [`cse473_lab.py:495-528`](file:///e:/ai%20forge/backend/clipforge_engine/cse473_lab.py#L495-L528). |
| **39**| **Local Offline Edge Deployment** | **IMPLEMENTED** | 100% offline deployment with local Ollama (`qwen2.5:3b`, `nomic-embed-text`) and local Whisper. [`main.py`](file:///e:/ai%20forge/backend/clipforge_engine/main.py), [`app.py`](file:///e:/ai%20forge/app.py). |
| **40**| **Multi-Modal Video / Audio Ingestion** | **IMPLEMENTED** | Full audio extraction, Whisper STT, OpenCV scene detection, and FFmpeg video burning. [`pipeline.py:100-350`](file:///e:/ai%20forge/backend/clipforge_engine/pipeline.py#L100-L350). |
