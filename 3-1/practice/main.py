from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
import os
import httpx
import logging
from azure.identity import get_bearer_token_provider, DefaultAzureCredential
from openai import AzureOpenAI
from typing import Optional
import json

OPENAI_API_ENDPOINT = os.getenv('OPENAI_API_ENDPOINT')
OPENAI_DEPLOYMENT_NAME = os.getenv('OPENAI_DEPLOYMENT_NAME')
OPENAI_API_VERSION = os.getenv('OPENAI_API_VERSION')

logging.basicConfig(
    level=logging.INFO
)
logger=logging.getLogger(__name__)

app = FastAPI(
    title="hey",
    description='yo',
    version='v1'
)


@app.get('/healthz')
async def get_health():
    return {'status': 'healthy'}

@app.get('/readyz')
async def readiness_probe():
    try:
        with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.head(OPENAI_API_ENDPOINT)
            if response.status_code < 500:
                return {'status':'ready'}
    except Exception as e:
        logger.error(f'foundry connectivity check failed: {e}')

    raise HTTPException(status_code=503, detail="no")

token_provider = get_bearer_token_provider(
    DefaultAzureCredential(),
    "https://cognitiveservices.azure.com/.default"
)

def get_openai_client() -> AzureOpenAI:
    return AzureOpenAI(
        api_version=OPENAI_API_VERSION,
        azure_endpoint=OPENAI_API_ENDPOINT,
        azure_ad_token_provider=token_provider
    )

def call_foundry_inference(
        prompt: str,
        parameters: Optional[dict] = None,
):
    try:
        client = get_openai_client()
        response = client.chat.completions.create(
            model=OPENAI_DEPLOYMENT_NAME,
            stream=False,
            messages=[{"role":"user", "content": prompt}],
            max_completion_tokens=16384
        )
        return response.model_dump()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"foundry unmavailbe: {e}")
    

@app.post('/v1/inference')
async def synchronous_inference(request: Request):
    try:
        body = await body.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"body not defined: {e}")

    prompt = body.get('inputs',{}).get('prompt')
    parameters = body.get('parameters',{})

    try:
        response = call_foundry_inference(prompt, parameters) 
        return response
    except HTTPException:
        raise;
    except Exception as e:
        raise HTTPException(status_code=503,detail='failed: {e}')

@app.post('/v1/inference/stream')
async def stream_inference(request: Request):
    try:
        body = await request.json();
    except Exception as e:
        raise HTTPException(status_code=503, detail='de')

    prompt = request.get('inputs',{}).get('prompt')
    parameters = request.get('parameters',{})


    async def event_generator():
        client = get_openai_client()
        response = client.chat.completions.create(
            model=OPENAI_DEPLOYMENT_NAME,
            stream=True,
            messages=[{"role":"user", "content": prompt}],
            max_completion_tokens=16384
        )

        for chunk in response:
            if chunk.choices[0] and chunk.choices[0].delta.content:
                data = {
                    "choices": [{
                        "delta": {
                            "content": chunk.choices[0].delta.content
                        }
                    }]
                }

                yield f"data: {json.dumps(data)}\n\n"
        yield f"data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )