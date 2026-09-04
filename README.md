<div align="center">
  <img src="assets/banner.jpg" alt="Facial Recognition Event Attendance Banner" width="100%">
  <br>
  <h1>🤖 Smart Event Attendance System</h1>
  <p><strong>A highly optimized, AI-driven facial recognition framework for real-time event attendance.</strong></p>
</div>

<br>

## 📖 Overview

The **Smart Event Attendance System** is a robust and scalable solution designed to automate event check-ins using advanced facial recognition. By leveraging deep learning models and high-performance vector search databases, the system offers ultra-low latency inference, minimizing false alarms and ensuring strict attendance control.

This project was built with a strong focus on **Data Engineering** and **AI System Architecture**, implementing automated data pipelines for feature extraction, storage, and real-time inference.

---

## ✨ Key Features

- **🧠 Real-Time Inference (InsightFace):** Utilizes the `buffalo_l` model for highly accurate face detection and feature extraction.
- **⚡ Lightning-Fast Vector Search (FAISS):** Embeddings are indexed using Facebook AI Similarity Search (FAISS) for sub-millisecond retrieval.
- **🛡️ AI Voting Logic:** Employs a Top-10 Nearest Neighbors voting mechanism in FAISS to drastically reduce false positives and ensure accurate identification.
- **📈 Gallery Enrichment (Auto-Learning):** The system continuously enriches its dataset by capturing and storing new facial vectors during real-time attendance when confidence scores exceed `0.75`.
- **🔐 Strict Access Control:** Enforces strict attendance logic, ensuring only pre-assigned individuals can check in, preventing unauthorized access.
- **🐳 Dockerized Architecture:** Fully containerized backend, frontend, and database services optimized for seamless deployment across environments (including Windows I/O watchfile optimizations).

---

## 🛠️ Technology Stack

- **Backend:** Python 3.11, FastAPI, WebSocket
- **AI/ML:** InsightFace, OpenCV, FAISS (Facebook AI Similarity Search)
- **Database:** PostgreSQL (asyncpg)
- **Frontend:** React, Vite, Tailwind CSS
- **DevOps:** Docker, Docker Compose, Nginx

---

## 🚀 Quick Start (Development)

### 1. Database Setup
Ensure PostgreSQL is running on port `5432` and create a database named `attendance`. Alternatively, you can spin it up using Docker Compose.

### 2. Backend Setup
```bash
cd backend
python -m venv .venv
# Activate virtual environment (Windows)
.venv\Scripts\activate 
# Install dependencies
pip install -r requirements.txt

# Set database URL
set DATABASE_URL=postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/attendance

# Run the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
*Note: On the first run, InsightFace will automatically download the `buffalo_l` model.*

### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
Access the application at `http://127.0.0.1:5173`. API requests will be proxied to the backend at port `8000`.

---

## 🐳 Docker Deployment (All-in-One)

Deploy the entire stack seamlessly using Docker.

```bash
cd docker
docker compose up --build
```
- **UI Dashboard:** `http://localhost:8080`
- **REST API:** `http://localhost:8080/api/...`
- **WebSocket:** `ws://localhost:8080/api/ws/live?...`

*Windows Users: Ensure Docker Desktop is running. If using WSL2, execute the `docker compose` command inside the WSL terminal.*

---

## 📂 Project Structure

```text
├── backend/          # FastAPI server, WebSocket, FAISS logic, InsightFace pipeline
├── frontend/         # React + Vite application, webcam streaming, analytics dashboard
├── database/         # SQL initialization scripts (init.sql) and schemas
├── faiss_indexes/    # Persistent storage for FAISS index files and metadata JSON
├── docker/           # Dockerfiles, Compose configs, and Nginx reverse proxy
└── assets/           # Project images and banners
```
