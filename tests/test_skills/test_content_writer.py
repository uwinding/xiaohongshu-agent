from unittest.mock import MagicMock
from app.llm_client import LLMClient, LLMResponse
from app.skills.content_writer import ContentWriter


def make_llm() -> LLMClient:
    client = MagicMock(spec=LLMClient)
    client.model = "gpt-4o"
    return client


def test_content_writer_success():
    llm = make_llm()
    llm.chat.return_value = LLMResponse(
        content='{"title":"小个子夏季穿搭，腰线一高比例就出来了",'
        '"content":"姐妹们！今天一定要分享这套法式穿搭\\n\\n'
        '碎花A字连衣裙真的太适合我们小个子女生了，V领设计拉长颈部线条...\\n'
        '搭配高腰阔腿裤，整体比例拉满！",'
        '"hashtags":["小个子穿搭","法式穿搭","显瘦穿搭","夏季穿搭","OOTD"],'
        '"product_tags":[{"name":"法式碎花连衣裙","url":"https://example.com/product/1"}]}',
        model="gpt-4o",
        tokens_used=400,
    )

    writer = ContentWriter(llm)
    result = writer.execute(
        outfit_desc="法式碎花连衣裙搭配高腰阔腿裤",
        products=[{"name": "法式碎花连衣裙", "source_url": "https://example.com/product/1"}],
        persona={"tone_of_voice": "亲切轻松，像朋友分享穿搭经验", "body_type": "小个子", "style_tags": ["甜美", "韩系"]},
    )

    assert result.success
    assert len(result.data["title"]) > 5
    assert len(result.data["hashtags"]) >= 3
    assert len(result.data["product_tags"]) >= 1


def test_content_writer_empty_outfit():
    llm = make_llm()
    writer = ContentWriter(llm)
    result = writer.execute(outfit_desc="", products=[], persona={})
    assert not result.success
    assert "Empty outfit" in result.error
