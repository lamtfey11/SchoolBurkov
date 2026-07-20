"""
Загрузка данных для дашборда школы Буркова.

Два источника:
1. Готовые JSON-файлы, которые ноутбук main.ipynb уже умеет сохранять
   (factors.json, author_year_vectors_sid=....json,
   author_overall_vectors_sid=....json, author_fio.json).
2. Прямой запрос к API (та же логика, что в ноутбуке, только без
   ipywidgets и с прогресс-баром для Streamlit).
"""

import json
import time

import requests

API_BASE = "http://193.232.208.28/api/v2.5"


def fetch_factors() -> dict:
    """Скачивает три уровня классификации тем и объединяет их в один словарь.

    Возвращает: {"0": {...}, "1": {...}, "2": {...}}, аналогично factors.json
    из ноутбука.
    """
    factors_by_level = {}
    for level in (0, 1, 2):
        resp = requests.get(
            f"{API_BASE}/classifications/get_factors",
            params={"clf_level": level},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        factors_by_level[str(level)] = {
            str(item["c_f_id"]): item["c_f_name"] for item in data
        }
    return factors_by_level


def fetch_author_year_vectors(author_ids, sid, begin, end, progress_callback=None) -> dict:
    """Погодовые тематические профили каждого автора."""
    data = {}
    total = max(len(author_ids), 1)
    for i, author_id in enumerate(author_ids):
        data[str(author_id)] = {}
        for year in range(begin, end + 1):
            params = {"id": author_id, "sid": sid, "begin_year": year, "end_year": year}
            try:
                resp = requests.get(
                    f"{API_BASE}/authors/analysis/get_profile", params=params, timeout=10
                )
                profile = resp.json()
                if "factors" in profile:
                    data[str(author_id)][str(year)] = profile["factors"]
            except requests.exceptions.RequestException:
                pass
        if progress_callback:
            progress_callback((i + 1) / total)
    return data


def fetch_author_overall_vectors(author_ids, sid, begin, end, progress_callback=None) -> dict:
    """Обобщённый тематический профиль автора за весь период begin..end."""
    data = {}
    total = max(len(author_ids), 1)
    for i, author_id in enumerate(author_ids):
        params = {"id": author_id, "sid": sid, "begin_year": begin, "end_year": end}
        try:
            resp = requests.get(
                f"{API_BASE}/authors/analysis/get_profile", params=params, timeout=10
            )
            profile = resp.json()
            if "factors" in profile:
                data[str(author_id)] = profile["factors"]
        except requests.exceptions.RequestException:
            pass
        if progress_callback:
            progress_callback((i + 1) / total)
    return data


def fetch_author_fio(author_ids, progress_callback=None) -> dict:
    """ФИО авторов по их id."""
    data = {}
    total = max(len(author_ids), 1)
    for i, author_id in enumerate(author_ids):
        try:
            resp = requests.get(
                f"{API_BASE}/authors/search", params={"id": author_id}, timeout=15
            )
            profile = resp.json()
            if profile:
                person = profile[0]
                data[str(author_id)] = {
                    "last_name": person.get("last_name", ""),
                    "first_name": person.get("first_name", ""),
                    "sec_name": person.get("sec_name", ""),
                }
        except requests.exceptions.RequestException:
            pass
        time.sleep(0.3)  # чтобы не заваливать сервер запросами, как в ноутбуке
        if progress_callback:
            progress_callback((i + 1) / total)
    return data


def load_json(file_obj_or_path):
    """Читает JSON либо из загруженного в Streamlit файла, либо с диска."""
    if hasattr(file_obj_or_path, "read"):
        return json.load(file_obj_or_path)
    with open(file_obj_or_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(obj, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
