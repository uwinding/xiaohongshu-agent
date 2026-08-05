from unittest.mock import patch, MagicMock
from app.models import BloggerPersona, Product, GeneratedPost, Outfit


def seed_persona(db):
    p = BloggerPersona(name="测试博主", body_type="小个子", style_tags=["法式"])
    db.add(p)
    db.commit()
    return p


def seed_product(db):
    prod = Product(name="测试连衣裙", category="裙装", price=199.0)
    db.add(prod)
    db.commit()
    return prod


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_generate_post(client, setup_db):
    seed_persona(setup_db)
    seed_product(setup_db)

    with patch("app.routes.generate.pipeline") as mock_pipeline:
        mock_pipeline.run.return_value = {
            "post": {"id": 1, "title": "测试", "status": "draft", "outfit_id": 1,
                     "images": [], "content": "", "hashtags": [], "product_tags": [],
                     "created_at": "2025-01-01T00:00:00", "published_at": None},
            "outfit": {"id": 1, "description": "测试", "product_ids": [], "pos_prompt": "",
                       "neg_prompt": "", "style_tags": [], "scene": "", "body_type_suitability": "",
                       "created_at": "2025-01-01T00:00:00"},
            "images": ["/tmp/test.png"],
        }

        response = client.post("/api/generate", json={"persona_id": 1})
        assert response.status_code == 200
        data = response.json()
        assert data["post"]["title"] == "测试"


def test_list_posts(client, setup_db):
    seed_persona(setup_db)

    outfit = Outfit(description="测试穿搭", pos_prompt="test")
    setup_db.add(outfit)
    setup_db.commit()

    post = GeneratedPost(outfit_id=outfit.id, title="测试帖子", content="测试内容", status="draft")
    setup_db.add(post)
    setup_db.commit()

    response = client.get("/api/posts")
    assert response.status_code == 200
    posts = response.json()
    assert len(posts) >= 1
    assert posts[0]["title"] == "测试帖子"


def test_update_post_status(client, setup_db):
    seed_persona(setup_db)
    outfit = Outfit(description="测试穿搭", pos_prompt="test")
    setup_db.add(outfit)
    setup_db.commit()

    post = GeneratedPost(outfit_id=outfit.id, title="待审核", content="内容", status="draft")
    setup_db.add(post)
    setup_db.commit()

    response = client.patch(f"/api/posts/{post.id}", json={"status": "reviewed"})
    assert response.status_code == 200
    assert response.json()["status"] == "reviewed"


def test_get_trends(client):
    response = client.get("/api/trends")
    assert response.status_code == 200
    assert response.json() == []
