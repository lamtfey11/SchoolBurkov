"""
Вся расчётная логика из main.ipynb, но без глобальной переменной `sid`
и без ipywidgets — вместо этого чистые функции, которые Streamlit-приложение
вызывает с явными параметрами.
"""

import math

import numpy as np
from scipy.cluster.hierarchy import dendrogram, linkage
from scipy.spatial.distance import squareform
from scipy.stats import linregress
from sklearn.cluster import AgglomerativeClustering
from sklearn.decomposition import PCA
from sklearn.metrics.pairwise import cosine_similarity


def get_level(sid) -> str:
    """clf_level зависит от второй цифры sid (110 -> '1', 120 -> '2')."""
    return str(sid)[1]


def build_fio_string(author_id, data_fio) -> str:
    person = data_fio.get(str(author_id))
    if not person:
        return f"Автор #{author_id}"
    parts = [person.get("last_name", ""), person.get("first_name", ""), person.get("sec_name", "")]
    fio = " ".join(p for p in parts if p).strip()
    return fio or f"Автор #{author_id}"


def sorted_author_vector(data_overall, author_id) -> dict:
    vec = data_overall.get(str(author_id), {})
    return dict(sorted(vec.items(), key=lambda item: -item[1]))


def compute_entropy(vector: dict):
    """Возвращает (H, H_norm). H_norm ближе к 1 — универсал, ближе к 0 — узкий специалист."""
    if not vector:
        return 0.0, 0.0
    H = 0.0
    for w in vector.values():
        if w > 0:
            H -= w * math.log2(w)
    n = len(vector)
    H_norm = H / math.log2(n) if n > 1 else 0.0
    return H, H_norm


def top_topic_by_year(author_id, data_vectors) -> dict:
    """{year: (topic_id, weight)} — тема-лидер автора в каждом году."""
    data = data_vectors.get(str(author_id), {})
    result = {}
    for year, vec in data.items():
        if not vec:
            continue
        topic_id, weight = max(vec.items(), key=lambda item: item[1])
        result[year] = (topic_id, weight)
    return dict(sorted(result.items(), key=lambda kv: int(kv[0])))


def entropy_by_year(author_id, data_vectors) -> dict:
    data = data_vectors.get(str(author_id), {})
    result = {}
    for year, vec in data.items():
        result[year] = compute_entropy(vec)
    return dict(sorted(result.items(), key=lambda kv: int(kv[0])))


def author_trajectory(author_id, data_vectors, all_topic_ids):
    """PCA-траектория автора в пространстве тем по годам."""
    data = data_vectors.get(str(author_id), {})
    years = sorted(data.keys(), key=int)
    if len(years) < 2:
        return years, None, None
    matrix = np.array([[data[y].get(tid, 0) for tid in all_topic_ids] for y in years])
    pca = PCA(n_components=2)
    coords = pca.fit_transform(matrix)
    return years, coords, pca.explained_variance_ratio_


def proximity_matrix_overall(data_overall, all_topic_ids):
    author_ids = list(data_overall.keys())
    matrix = np.array(
        [[data_overall[aid].get(tid, 0) for tid in all_topic_ids] for aid in author_ids]
    )
    similarity_matrix = cosine_similarity(matrix)
    return similarity_matrix, author_ids


def closest_authors(similarity_matrix, author_ids, author_id, data_fio, top_n=10):
    idx = author_ids.index(str(author_id))
    sims = similarity_matrix[idx]
    result = [
        (build_fio_string(author_ids[i], data_fio), author_ids[i], float(sims[i]))
        for i in range(len(author_ids))
        if i != idx
    ]
    result.sort(key=lambda x: -x[2])
    return result[:top_n] if top_n else result


def hierarchical_order(similarity_matrix, author_ids):
    """Порядок авторов после иерархической кластеризации (как в sns.clustermap)."""
    distance_matrix = 1 - similarity_matrix
    np.fill_diagonal(distance_matrix, 0)
    condensed = squareform(distance_matrix, checks=False)
    Z = linkage(condensed, method="average")
    order = dendrogram(Z, no_plot=True)["leaves"]
    return order, Z


def cluster_authors(similarity_matrix, author_ids, data_fio, n_clusters=12):
    distance_matrix = 1 - similarity_matrix
    clustering = AgglomerativeClustering(
        n_clusters=n_clusters, metric="precomputed", linkage="average"
    )
    labels = clustering.fit_predict(distance_matrix)
    clusters = {}
    for aid, label in zip(author_ids, labels):
        clusters.setdefault(int(label), []).append(build_fio_string(aid, data_fio))
    return clusters


def entropy_all_authors(data_overall, data_fio):
    """Список (fio, author_id, H, H_norm), отсортированный от самых разносторонних."""
    results = []
    for author_id, vector in data_overall.items():
        fio = build_fio_string(author_id, data_fio)
        H, H_norm = compute_entropy(vector)
        results.append((fio, author_id, H, H_norm))
    results.sort(key=lambda x: -x[3])
    return results


def school_vector_for_year(year, data_vectors):
    year = str(year)
    result, n_authors = {}, 0
    for _, yearly_data in data_vectors.items():
        if year in yearly_data:
            for topic_id, weight in yearly_data[year].items():
                result[topic_id] = result.get(topic_id, 0) + weight
            n_authors += 1
    if n_authors == 0:
        return {}, 0
    return {tid: total / n_authors for tid, total in result.items()}, n_authors


def school_vectors_all_years(data_vectors, start_year=2000, end_year=2025):
    all_years_data = {}
    for year in range(start_year, end_year + 1):
        vector, n_authors = school_vector_for_year(year, data_vectors)
        if n_authors > 0:
            all_years_data[year] = {"vector": vector, "n_authors": n_authors}
    return all_years_data


def top_school_topics(school_by_year, top_n):
    years = sorted(school_by_year.keys())
    avg_weights = {}
    for year in years:
        for tid, w in school_by_year[year]["vector"].items():
            avg_weights[tid] = avg_weights.get(tid, 0) + w
    for tid in avg_weights:
        avg_weights[tid] /= len(years)
    top_topics = sorted(avg_weights.items(), key=lambda x: -x[1])[:top_n]
    return top_topics, years


def compute_topic_trends(school_by_year):
    years = sorted(school_by_year.keys())
    all_topic_ids = set()
    for year in years:
        all_topic_ids.update(school_by_year[year]["vector"].keys())
    trends = {}
    for topic_id in all_topic_ids:
        values = [school_by_year[year]["vector"].get(topic_id, 0) for year in years]
        r = linregress(years, values)
        trends[topic_id] = {
            "slope": r.slope,
            "intercept": r.intercept,
            "r_value": r.rvalue,
            "p_value": r.pvalue,
        }
    return trends


def compute_topic_reach(data_overall, factors_map, threshold=0.05):
    topic_author_count = {}
    for _, vector in data_overall.items():
        for topic_id, weight in vector.items():
            if weight >= threshold:
                topic_author_count[topic_id] = topic_author_count.get(topic_id, 0) + 1
    for topic_id in factors_map.keys():
        topic_author_count.setdefault(topic_id, 0)
    return topic_author_count


def forecast_topic(school_by_year, trends, topic_id, forecast_years=5):
    """Экстраполяция линейного тренда темы на forecast_years лет вперёд.

    Возвращает (years, values, future_years, forecast_values, slope_pp, p_value):
      - years/values       -- фактические данные по годам, в %
      - future_years/forecast_values -- прогноз, в %, с защитой от ухода в минус
      - slope_pp           -- наклон тренда в п.п./год
      - p_value            -- значимость тренда (из linregress)
    """
    years = sorted(school_by_year.keys())
    values = [school_by_year[year]["vector"].get(topic_id, 0) * 100 for year in years]

    trend_data = trends[topic_id]
    slope = trend_data["slope"] * 100
    intercept = trend_data["intercept"] * 100
    p_value = trend_data["p_value"]

    last_year = years[-1]
    future_years = list(range(last_year, last_year + forecast_years + 1))
    forecast_values = [max(0, slope * y + intercept) for y in future_years]

    return years, values, future_years, forecast_values, slope, p_value
