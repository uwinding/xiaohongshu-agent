from app.models import BloggerPersona, Product, Outfit, GeneratedPost, PostPerformance, Trend


def test_create_persona(setup_db):
    persona = BloggerPersona(
        name="测试博主",
        body_type="小个子",
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
    persona = BloggerPersona(name="测试", body_type="小个子")
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


def test_create_trend(setup_db):
    trend = Trend(
        keyword="法式穿搭",
        category="时尚",
        hot_score=9500,
        source_posts=["https://example.com/trend/1"],
    )
    setup_db.add(trend)
    setup_db.commit()
    assert trend.id is not None
    assert trend.keyword == "法式穿搭"
    assert trend.hot_score == 9500


def test_create_outfit_full(setup_db):
    outfit = Outfit(
        product_ids=[1, 2],
        description="法式通勤穿搭",
        pos_prompt="优雅小个子女装，法式风格，办公室场景",
        neg_prompt="紧身，低腰，廉价材质",
        style_tags=["法式", "通勤", "小个子"],
        scene="办公室",
        body_type_suitability="小个子",
    )
    setup_db.add(outfit)
    setup_db.commit()
    assert outfit.id is not None
    assert outfit.pos_prompt is not None
    assert outfit.neg_prompt is not None
    assert outfit.style_tags == ["法式", "通勤", "小个子"]
    assert outfit.scene == "办公室"
    assert outfit.body_type_suitability == "小个子"
