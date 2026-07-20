"""
Дашборд «Тематическая структура школы Буркова».

Запуск:
    streamlit run app.py

Логика полностью перенесена из main.ipynb: та же работа с API, те же
расчёты (энтропия, косинусная близость, PCA-траектория, тренды по годам,
прогноз по теме), но matplotlib/seaborn/ipywidgets заменены на Plotly +
виджеты Streamlit, чтобы всё открывалось в обычной браузерной странице.
"""

import pandas as pd
import streamlit as st

import analysis as an
import charts as ch
from data_io import (
    fetch_author_fio,
    fetch_author_overall_vectors,
    fetch_author_year_vectors,
    fetch_factors,
    load_json,
)

st.set_page_config(page_title="Школа Буркова — тематическая аналитика", layout="wide")

# ---------------------------------------------------------------------------
# Состояние сессии
# ---------------------------------------------------------------------------
for key in ("factors_by_level", "data_vectors", "data_overall", "data_fio", "sid"):
    st.session_state.setdefault(key, None)

st.title("Анализ тематической структуры школы Буркова")

# ---------------------------------------------------------------------------
# Сайдбар: загрузка данных
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("Данные")
    source = st.radio(
        "Источник данных",
        ["Загрузить готовые JSON", "Запросить через API"],
        help="JSON-файлы — те же, что main.ipynb сохраняет на диск в разделе 2.",
    )

    if source == "Загрузить готовые JSON":
        f_factors = st.file_uploader("factors.json", type="json")
        f_vectors = st.file_uploader("author_year_vectors_sid=….json", type="json")
        f_overall = st.file_uploader("author_overall_vectors_sid=….json", type="json")
        f_fio = st.file_uploader("author_fio.json", type="json")
        sid_input = st.number_input("sid (тип профиля)", min_value=100, max_value=999, value=110, step=1)

        if st.button("Загрузить в приложение", type="primary"):
            try:
                if f_factors is not None:
                    st.session_state.factors_by_level = load_json(f_factors)
                if f_vectors is not None:
                    st.session_state.data_vectors = load_json(f_vectors)
                if f_overall is not None:
                    st.session_state.data_overall = load_json(f_overall)
                if f_fio is not None:
                    st.session_state.data_fio = load_json(f_fio)
                st.session_state.sid = int(sid_input)
                st.success("Данные загружены")
            except Exception as e:
                st.error(f"Ошибка загрузки: {e}")

    else:
        st.caption("Запросы идут напрямую к API школы Буркова — нужен доступ к этой сети.")
        csv_file = st.file_uploader("CSV со списком авторов (колонка id)", type="csv")
        sid_input = st.selectbox("sid (тип профиля)", [100, 110, 120, 200, 210, 220], index=1)
        col1, col2 = st.columns(2)
        begin_input = col1.number_input("Год начала", min_value=2000, max_value=2030, value=2015)
        end_input = col2.number_input("Год конца", min_value=2000, max_value=2030, value=2025)

        if csv_file is not None and st.button("Загрузить данные с API", type="primary"):
            df = pd.read_csv(csv_file)
            author_ids = df["id"].tolist()

            with st.spinner("Загружаем справочник тем (факторов)..."):
                st.session_state.factors_by_level = fetch_factors()

            bar1 = st.progress(0.0, text="Погодовые профили авторов...")
            st.session_state.data_vectors = fetch_author_year_vectors(
                author_ids, sid_input, begin_input, end_input,
                progress_callback=lambda p: bar1.progress(p, text="Погодовые профили авторов..."),
            )

            bar2 = st.progress(0.0, text="Обобщённые профили авторов...")
            st.session_state.data_overall = fetch_author_overall_vectors(
                author_ids, sid_input, begin_input, end_input,
                progress_callback=lambda p: bar2.progress(p, text="Обобщённые профили авторов..."),
            )

            bar3 = st.progress(0.0, text="ФИО авторов...")
            st.session_state.data_fio = fetch_author_fio(
                author_ids, progress_callback=lambda p: bar3.progress(p, text="ФИО авторов..."),
            )

            st.session_state.sid = int(sid_input)
            st.success("Данные загружены с API")

    st.divider()
    if st.session_state.data_overall:
        st.caption(f"Авторов в данных: {len(st.session_state.data_overall)}")

# ---------------------------------------------------------------------------
# Проверка готовности данных
# ---------------------------------------------------------------------------
ready = all(
    st.session_state[k] for k in ("factors_by_level", "data_vectors", "data_overall", "data_fio", "sid")
)
if not ready:
    st.info("Загрузите данные в панели слева, чтобы начать анализ.")
    st.stop()

sid = st.session_state.sid
level = an.get_level(sid)
factors_map = st.session_state.factors_by_level[level]
data_vectors = st.session_state.data_vectors
data_overall = st.session_state.data_overall
data_fio = st.session_state.data_fio
all_topic_ids = list(factors_map.keys())

author_options = {
    an.build_fio_string(aid, data_fio) + f" (id={aid})": str(aid) for aid in data_fio.keys()
}

tab1, tab2, tab3 = st.tabs(["Профиль автора", "Сравнение авторов", "Динамика школы"])

# ---------------------------------------------------------------------------
# Вкладка 1 — одиночный автор (аналог раздела 3.1 ноутбука)
# ---------------------------------------------------------------------------
with tab1:
    selected_label = st.selectbox("Автор", list(author_options.keys()), key="author_select")
    author_id = author_options[selected_label]
    fio = an.build_fio_string(author_id, data_fio)

    vector_sorted = an.sorted_author_vector(data_overall, author_id)
    H, H_norm = an.compute_entropy(data_overall.get(str(author_id), {}))

    c1, c2 = st.columns(2)
    c1.metric("Энтропия", f"{H:.3f}")
    c2.metric("Нормированная энтропия (широта охвата)", f"{H_norm * 100:.1f}%")
    st.caption(
        "Чем ближе к 100% — тем более разносторонний автор (универсал). "
        "Чем ближе к 0% — тем более узкий специалист, сфокусированный на 1–2 темах."
    )

    st.plotly_chart(ch.fig_author_profile(vector_sorted, factors_map, fio), use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        top_year = an.top_topic_by_year(author_id, data_vectors)
        if top_year:
            st.plotly_chart(ch.fig_top_year(top_year, factors_map), use_container_width=True)
    with col2:
        ent_year = an.entropy_by_year(author_id, data_vectors)
        if ent_year:
            st.plotly_chart(ch.fig_entropy_by_year(ent_year), use_container_width=True)

    years, coords, explained_var = an.author_trajectory(author_id, data_vectors, all_topic_ids)
    if coords is not None:
        st.plotly_chart(ch.fig_trajectory(years, coords, explained_var, fio), use_container_width=True)
    else:
        st.caption("Недостаточно лет с данными для построения траектории (нужно минимум 2 года).")

# ---------------------------------------------------------------------------
# Вкладка 2 — сравнение авторов (аналог раздела 3.2 ноутбука)
# ---------------------------------------------------------------------------
with tab2:
    similarity_matrix, author_ids = an.proximity_matrix_overall(data_overall, all_topic_ids)
    labels = [an.build_fio_string(aid, data_fio) for aid in author_ids]

    reorder = st.checkbox("Переупорядочить по кластерам (как дендрограмма)", value=True)
    order = an.hierarchical_order(similarity_matrix, author_ids)[0] if reorder else None
    st.plotly_chart(
        ch.fig_similarity_heatmap(similarity_matrix, labels, order=order), use_container_width=True
    )

    with st.expander("Кластеризация авторов"):
        max_clusters = max(2, len(author_ids) - 1)
        n_clusters = st.slider("Число кластеров", 2, max_clusters, min(12, max_clusters))
        clusters = an.cluster_authors(similarity_matrix, author_ids, data_fio, n_clusters=n_clusters)
        for cluster_id in sorted(clusters.keys()):
            members = clusters[cluster_id]
            st.markdown(f"**Кластер {cluster_id + 1} ({len(members)} чел.)**")
            st.write(", ".join(members))

    st.subheader("Рейтинг разносторонности авторов")
    results = an.entropy_all_authors(data_overall, data_fio)
    top_n_entropy = st.slider("Сколько авторов показать", 5, len(results), min(20, len(results)))
    st.plotly_chart(ch.fig_entropy_ranking(results, top_n=top_n_entropy), use_container_width=True)

    st.subheader("Близость к выбранному автору")
    selected_label2 = st.selectbox("Автор", list(author_options.keys()), key="author_select_compare")
    author_id2 = author_options[selected_label2]
    max_neighbors = max(1, len(author_ids) - 1)
    n_neighbors = st.slider(
        "Сколько ближайших авторов показать", 1, max_neighbors, min(15, max_neighbors),
        key="closest_authors_n",
    )
    closest = an.closest_authors(similarity_matrix, author_ids, author_id2, data_fio, top_n=n_neighbors)
    st.plotly_chart(ch.fig_closest_authors(closest), use_container_width=True)

# ---------------------------------------------------------------------------
# Вкладка 3 — динамика школы по годам (аналог раздела 3.3 ноутбука)
# ---------------------------------------------------------------------------
with tab3:
    all_years = [int(y) for author in data_vectors.values() for y in author.keys()]
    min_year, max_year = (min(all_years), max(all_years)) if all_years else (2000, 2025)

    school_by_year = an.school_vectors_all_years(data_vectors, start_year=min_year, end_year=max_year)

    if not school_by_year:
        st.warning("Нет погодовых данных для построения динамики школы.")
    else:
        top_n = st.slider("Количество тем в топе", 1, len(factors_map), min(5, len(factors_map)))
        top_topics, years = an.top_school_topics(school_by_year, top_n)
        top_topic_ids = [t[0] for t in top_topics]
        top_topic_names = [factors_map.get(tid, tid) for tid in top_topic_ids]

        st.plotly_chart(ch.fig_school_topic_top(top_topics, factors_map), use_container_width=True)

        st.caption("Показаны темы: " + "; ".join(top_topic_names))
        selected_names = st.multiselect(
            "Какие темы показать на графике динамики (по умолчанию — топ выше)",
            options=list(factors_map.values()),
            default=top_topic_names,
            key="dynamics_topic_select",
        )
        name_to_id = {name: tid for tid, name in factors_map.items()}
        selected_ids = [name_to_id[name] for name in selected_names if name in name_to_id]
        if selected_ids:
            st.plotly_chart(
                ch.fig_school_topic_dynamics(school_by_year, selected_ids, factors_map, years),
                use_container_width=True,
            )
        else:
            st.caption("Выберите хотя бы одну тему, чтобы построить график динамики.")

        st.subheader("Тренды тем (линейная регрессия по годам)")
        max_trend = max(1, len(factors_map) // 2)
        trend_top_n = st.slider("Сколько растущих/падающих тем показать", 1, max_trend, min(10, max_trend))
        trends = an.compute_topic_trends(school_by_year)
        st.plotly_chart(ch.fig_topic_trends(trends, factors_map, top_n=trend_top_n), use_container_width=True)

        st.subheader("Прогноз по отдельной теме")
        topic_name_to_id = {name: tid for tid, name in factors_map.items()}
        col_a, col_b = st.columns([2, 1])
        topic_choice = col_a.selectbox("Тема", list(topic_name_to_id.keys()), key="forecast_topic")
        forecast_years_n = col_b.slider("Лет вперёд", 1, 10, 5, key="forecast_years")
        topic_id_choice = topic_name_to_id[topic_choice]
        years_f, values_f, future_years_f, forecast_values_f, slope_f, p_f = an.forecast_topic(
            school_by_year, trends, topic_id_choice, forecast_years=forecast_years_n
        )
        st.plotly_chart(
            ch.fig_topic_forecast(
                years_f, values_f, future_years_f, forecast_values_f,
                topic_name=topic_choice, p_value=p_f,
            ),
            use_container_width=True,
        )
        if p_f >= 0.05:
            st.caption(
                "Обратите внимание: тренд статистически не значим (p ≥ 0.05), "
                "прогноз стоит воспринимать как ориентировочный."
            )

        st.subheader("Ядро vs периферия школы")
        threshold = st.slider("Порог значимости веса темы", 0.01, 0.30, 0.05, step=0.01)
        topic_reach = an.compute_topic_reach(data_overall, factors_map, threshold=threshold)
        st.plotly_chart(
            ch.fig_topic_reach(topic_reach, factors_map, threshold=threshold), use_container_width=True
        )

        st.subheader("Активность школы по годам")
        st.plotly_chart(ch.fig_school_activity(school_by_year), use_container_width=True)
