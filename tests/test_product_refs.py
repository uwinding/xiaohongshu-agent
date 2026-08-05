from app.product_refs import (
    is_direct_image_reference,
    is_product_page_url,
    parse_reference_list,
    split_product_references,
)


def test_split_product_references_moves_taobao_page_to_source_url():
    source_url, images = split_product_references({
        "source_url": "",
        "images": "https://detail.tmall.com/item.htm?id=1046619320114",
    })

    assert source_url == "https://detail.tmall.com/item.htm?id=1046619320114"
    assert images == []


def test_parse_json_images_and_protocol_relative_image_url():
    refs = parse_reference_list('["//img.alicdn.com/imgextra/i1/test.jpg", "https://example.com/a.webp"]')

    assert refs == [
        "https://img.alicdn.com/imgextra/i1/test.jpg",
        "https://example.com/a.webp",
    ]
    assert all(is_direct_image_reference(ref) for ref in refs)


def test_detail_page_is_not_direct_image():
    src = "https://item.taobao.com/item.htm?id=123"

    assert is_product_page_url(src)
    assert not is_direct_image_reference(src)
