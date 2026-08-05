from unittest.mock import patch, MagicMock
from app.scraper import fetch_xiaohongshu_trends


def make_mock_soup():
    soup = MagicMock()
    card1 = MagicMock()
    title1 = MagicMock()
    title1.get_text.return_value = "小个子法式连衣裙推荐 姐妹们冲"
    card1.select_one.return_value = title1
    card2 = MagicMock()
    title2 = MagicMock()
    title2.get_text.return_value = "通勤穿搭"
    card2.select_one.return_value = title2
    soup.select.return_value = [card1, card2]
    return soup


@patch("app.scraper.requests.get")
@patch("app.scraper.BeautifulSoup")
def test_fetch_trends_returns_keywords(mock_bs, mock_get):
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response
    mock_bs.return_value = make_mock_soup()

    result = fetch_xiaohongshu_trends(keyword="法式穿搭")
    assert len(result) > 0
    assert any("法式" in kw for kw in result)


@patch("app.scraper.requests.get")
def test_fetch_trends_handles_network_error(mock_get):
    import requests
    mock_get.side_effect = requests.ConnectionError("Network error")
    result = fetch_xiaohongshu_trends(keyword="test")
    assert result == []
