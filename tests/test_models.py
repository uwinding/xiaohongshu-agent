from app.models import BloggerPersona, Product, Outfit, GeneratedPost, PostPerformance, Trend


def test_create_persona(setup_db):
    persona = BloggerPersona(
        name="测试博主",
        body_type="大码",
        style_tags=["法式", "通勤"],
    )
    setup_db.add(persona)
    setup_db.commit()
    assert persona.id is not None


def test_create_product(setup_db):
    product = Product(
        name="测试连衣裙",
        category="裙装",
        price=199.0,
    )
    setup_db.add(product)
    setup_db.commit()
    assert product.id is not None


def test_create_post_chain(setup_db):
    persona = BloggerPersona(name="测试", body_type="大码")
    setup_db.add(persona)

    product = Product(name="裙子", price=150.0)
    setup_db.add(product)
    setup_db.commit()

    outfit = Outfit(
        product_ids=[product.id],
        description="测试穿搭",
        pos_prompt="test prompt",
    )
    setup_db.add(outfit)
    setup_db.commit()

    post = GeneratedPost(
        outfit_id=outfit.id,
        title="测试标题",
        content="测试内容",
    )
    setup_db.add(post)
    setup_db.commit()

    perf = PostPerformance(post_id=post.id, likes=100)
    setup_db.add(perf)
    setup_db.commit()
    assert perf.likes == 100
