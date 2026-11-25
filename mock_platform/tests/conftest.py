from contextlib import ExitStack
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import config
import data_builder
import main


@pytest.fixture(scope="session")
def du_lieu_shopee():
    return data_builder.dung_du_lieu_shopee()


@pytest.fixture(scope="session")
def du_lieu_tiktok():
    return data_builder.dung_du_lieu_tiktok()


@pytest.fixture(scope="session")
def cau_hinh():
    return config.doc_cau_hinh(Path(config.__file__).parent / ".env.example")


@pytest.fixture
def tao_client(du_lieu_shopee, du_lieu_tiktok):
    with ExitStack() as ngan_xep:
        def tao(cau_hinh, dong_ho):
            ung_dung = main.tao_ung_dung(
                cau_hinh, dong_ho=lambda: dong_ho["bay_gio"],
                du_lieu_shopee=du_lieu_shopee, du_lieu_tiktok=du_lieu_tiktok,
            )
            return ngan_xep.enter_context(TestClient(ung_dung))
        yield tao
