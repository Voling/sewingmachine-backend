from app.domain import models


def test_file_descriptor_to_dict():
    fd = models.FileDescriptor(key="k", size=10, last_modified="2024-01-01T00:00:00Z", url="url")
    assert fd.to_dict() == {
        "key": "k",
        "size": 10,
        "last_modified": "2024-01-01T00:00:00Z",
        "url": "url",
    }


def test_layer_snapshot_to_dict():
    file_desc = models.FileDescriptor(key="k", size=None, last_modified=None, url=None)
    directory = models.DirectoryDescriptor(
        name="n",
        prefix="p",
        file_count=1,
        files=[file_desc],
        truncated=False,
    )
    snapshot = models.LayerSnapshot(prefix="prefix", dir_count=1, dirs=[directory], truncated=False)
    payload = snapshot.to_dict()
    assert payload["dirs"][0]["files"][0]["key"] == "k"


def test_query_result_page_to_dict():
    stats = models.QueryStatistics(scanned_bytes=1, execution_time_ms=2)
    page = models.QueryResultPage(
        columns=["c1"],
        rows=[["v"]],
        stats=stats,
        query_execution_id="qid",
        next_page_token="next",
    )
    payload = page.to_dict()
    assert payload["stats"] == {"scanned_bytes": 1, "execution_time_ms": 2}
