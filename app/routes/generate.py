from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import GenerateRequest, GenerateResponse, PostOut, OutfitOut
from app.pipeline import GenerationPipeline

router = APIRouter(prefix="/api", tags=["generate"])
pipeline = GenerationPipeline()


@router.post("/generate", response_model=GenerateResponse)
def generate_post(req: GenerateRequest, db: Session = Depends(get_db)):
    result = pipeline.run(persona_id=req.persona_id, product_ids=req.product_ids, style=req.style, scene=req.scene)
    return GenerateResponse(post=PostOut(**result["post"]), outfit=OutfitOut(**result["outfit"]), generated_images=result["images"])
