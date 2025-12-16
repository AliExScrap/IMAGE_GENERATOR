from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
import httpx
import io

app = FastAPI()

MODELS = {
    "stable-diffusion": "stabilityai/stable-diffusion-2-1",
    "playground": "playgroundai/playground-v2.5-1024px-aesthetic",
    "sdxl": "stabilityai/stable-diffusion-xl-base-1.0"
}

@app.get("/", response_class=HTMLResponse)
async def home():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Générateur d'Images IA</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: 'Segoe UI', sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
                display: flex;
                justify-content: center;
                align-items: center;
            }
            .container {
                background: white;
                padding: 40px;
                border-radius: 20px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                max-width: 600px;
                width: 100%;
            }
            h1 {
                color: #667eea;
                text-align: center;
                margin-bottom: 30px;
                font-size: 32px;
            }
            label {
                display: block;
                margin: 15px 0 5px;
                font-weight: bold;
                color: #333;
            }
            input, select {
                width: 100%;
                padding: 12px;
                border-radius: 8px;
                border: 2px solid #ddd;
                font-size: 16px;
                transition: border-color 0.3s;
            }
            input:focus, select:focus {
                outline: none;
                border-color: #667eea;
            }
            button {
                width: 100%;
                padding: 15px;
                margin-top: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 18px;
                font-weight: bold;
                cursor: pointer;
                transition: transform 0.2s;
            }
            button:hover { transform: scale(1.02); }
            button:disabled {
                opacity: 0.5;
                cursor: not-allowed;
                transform: none;
            }
            .loading {
                display: none;
                text-align: center;
                margin-top: 20px;
                color: #667eea;
                font-weight: bold;
                animation: pulse 1.5s infinite;
            }
            @keyframes pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.5; }
            }
            #result {
                margin-top: 30px;
                text-align: center;
            }
            #result img {
                max-width: 100%;
                border-radius: 10px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                animation: fadeIn 0.5s;
            }
            @keyframes fadeIn {
                from { opacity: 0; transform: scale(0.9); }
                to { opacity: 1; transform: scale(1); }
            }
            .error {
                color: #ff6b6b;
                background: #ffe0e0;
                padding: 15px;
                border-radius: 8px;
                margin-top: 20px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎨 Générateur d'Images IA</h1>
            
            <label for="prompt">Description de l'image :</label>
            <input 
                type="text" 
                id="prompt" 
                placeholder="Ex: A beautiful sunset over mountains, digital art"
                onkeypress="handleEnter(event)"
            />
            
            <label for="model">Modèle :</label>
            <select id="model">
                <option value="stable-diffusion">Stable Diffusion 2.1</option>
                <option value="playground">Playground v2.5 (Haute qualité)</option>
                <option value="sdxl">Stable Diffusion XL</option>
            </select>
            
            <button onclick="generate()" id="generateBtn">✨ Générer l'image</button>
            
            <div class="loading" id="loading">
                ⏳ Génération en cours...<br>
                <small>Cela peut prendre 30-60 secondes</small>
            </div>
            
            <div id="result"></div>
        </div>

        <script>
            function handleEnter(event) {
                if (event.key === 'Enter') {
                    generate();
                }
            }

            async function generate() {
                const prompt = document.getElementById('prompt').value.trim();
                const model = document.getElementById('model').value;
                
                if (!prompt) {
                    alert('⚠️ Veuillez entrer une description');
                    return;
                }
                
                const btn = document.getElementById('generateBtn');
                const loading = document.getElementById('loading');
                const result = document.getElementById('result');
                
                btn.disabled = true;
                loading.style.display = 'block';
                result.innerHTML = '';
                
                try {
                    const response = await fetch('/generate', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ prompt, model })
                    });
                    
                    if (response.ok) {
                        const blob = await response.blob();
                        const url = URL.createObjectURL(blob);
                        result.innerHTML = `
                            <img src="${url}" alt="Generated image" />
                            <br><br>
                            <a href="${url}" download="generated-image.png">
                                <button style="width: auto; padding: 10px 20px;">
                                    💾 Télécharger
                                </button>
                            </a>
                        `;
                    } else {
                        const error = await response.json();
                        result.innerHTML = `
                            <div class="error">
                                ❌ Erreur: ${error.detail}
                            </div>
                        `;
                    }
                } catch (error) {
                    result.innerHTML = `
                        <div class="error">
                            ❌ Erreur de connexion: ${error.message}
                        </div>
                    `;
                }
                
                btn.disabled = false;
                loading.style.display = 'none';
            }
        </script>
    </body>
    </html>
    """

@app.post("/generate")
async def generate_image(request: dict):
    prompt = request.get("prompt", "")
    model_key = request.get("model", "stable-diffusion")
    
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt requis")
    
    model = MODELS.get(model_key, MODELS["stable-diffusion"])
    api_url = f"https://api-inference.huggingface.co/models/{model}"
    
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                api_url,
                json={"inputs": prompt},
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                return StreamingResponse(
                    io.BytesIO(response.content),
                    media_type="image/png"
                )
            elif response.status_code == 503:
                raise HTTPException(
                    status_code=503,
                    detail="Modèle en cours de chargement, réessayez dans 20 secondes"
                )
            else:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Erreur API: {response.text[:200]}"
                )
                
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Timeout - Réessayez")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    return {"status": "ok", "models": list(MODELS.keys())}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
