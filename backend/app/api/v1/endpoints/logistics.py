import pandas as pd
from app.ai.llm import process_query
from app.services.data_service import load_data
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


@router.get("/api/data")
async def get_shipment_data():
    df = load_data()
    # Replace NaN with None for JSON compatibility
    df = df.where(pd.notnull(df), None)
    # Convert to dict for JSON response
    # orient='records' gives list of dicts
    return df.to_dict(orient="records")


@router.websocket("/api/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    history: list = []  # per-session memory
    try:
        while True:
            data = await websocket.receive_text()
            df = load_data()
            response = process_query(data, df, history=history)
            await websocket.send_text(response)
    except WebSocketDisconnect:
        print("Client disconnected")
