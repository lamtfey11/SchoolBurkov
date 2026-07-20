"""
Все визуализации на Plotly — рендерятся как интерактивный HTML/JS и
работают в браузере (zoom, hover, легенда-фильтр), в отличие от
статичных PNG из matplotlib/seaborn в исходном ноутбуке.

Единая цветовая схема: мягкий, приглушённый розовый (почти к белому),
без ярких "светофорных" цветов, без эмодзи в подписях.
"""

import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# --- единая цветовая палитра приложения -----------------------------------
PRIMARY = "#D98A9B"        # основной цвет столбцов/линий
PRIMARY_DARK = "#B5657A"   # акцент — значимый / выделенный элемент
PRIMARY_SOFT = "#F1CDD6"   # светлый акцент
MUTED = "#C9BCC0"          # приглушённый (незначимо / вторично)
BLUSH = "#FBF1F3"          # почти белый розовый фон
INK = "#4A3B40"            # цвет текста / линий

# палитра для нескольких линий/категорий на одном графике — оттенки розового
LINE_PALETTE = [
    "#B5657A", "#D98A9B", "#E8AEB9", "#8C5866",
    "#F0C4CC", "#A6465C", "#DCA3AC", "#C97B88",
]

# монохромная розовая шкала для тепловой карты и траектории
PINK_SCALE = [[0.0, "#FFFFFF"], [0.5, "#F1CDD6"], [1.0, "#B5657A"]]


def _style(fig, height=None):
    """Единый базовый стиль для всех графиков приложения."""
    layout = dict(
        template="plotly_white",
        font=dict(family="Segoe UI, Arial, sans-serif", color=INK, size=13),
        colorway=LINE_PALETTE,
        title_font=dict(size=16, color=INK),
        margin=dict(t=60, b=40),
        plot_bgcolor="white",
        paper_bgcolor="white",
        hoverlabel=dict(bgcolor="white", font_color=INK),
    )
    if height:
        layout["height"] = height
    fig.update_layout(**layout)
    return fig


def fig_author_profile(vector_sorted: dict, factors_map: dict, fio: str):
    items = list(vector_sorted.items())
    names = [factors_map.get(tid, tid) for tid, _ in items]
    percents = [w * 100 for _, w in items]
    fig = go.Figure(
        go.Bar(
            x=percents[::-1], y=names[::-1], orientation="h",
            text=[f"{v:.1f}%" for v in percents[::-1]], textposition="outside",
            marker_color=PRIMARY,
        )
    )
    fig.update_layout(
        title=f"Тематический профиль: {fio}",
        xaxis_title="Доля, %",
        margin=dict(l=260),
    )
    return _style(fig, height=max(400, len(names) * 24))


def fig_top_year(top_year_dict: dict, factors_map: dict):
    years = list(top_year_dict.keys())
    topic_names = [factors_map.get(tid, tid) for tid, _ in top_year_dict.values()]
    weights = [w * 100 for _, w in top_year_dict.values()]
    fig = px.bar(
        x=years, y=[1] * len(years), color=topic_names,
        labels={"x": "Год", "color": "Тема"},
        hover_data={"Доля, %": [f"{w:.1f}" for w in weights]},
        color_discrete_sequence=LINE_PALETTE,
    )
    fig.update_layout(title="Топ-тема по годам", yaxis_visible=False, showlegend=True)
    return _style(fig)


def fig_entropy_by_year(entropy_dict: dict):
    years = [int(y) for y in entropy_dict.keys()]
    norms = [v[1] * 100 for v in entropy_dict.values()]
    fig = px.line(x=years, y=norms, markers=True, color_discrete_sequence=[PRIMARY])
    fig.update_layout(
        title="Динамика энтропии по годам", xaxis_title="Год",
        yaxis_title="Нормированная энтропия, %",
    )
    return _style(fig)


def fig_trajectory(years, coords, explained_var, fio):
    fig = go.Figure(
        go.Scatter(
            x=coords[:, 0], y=coords[:, 1], mode="lines+markers+text",
            text=years, textposition="top center",
            line=dict(color=PRIMARY_SOFT),
            marker=dict(
                size=11, color=[int(y) for y in years], colorscale=PINK_SCALE,
                colorbar=dict(title="Год"), line=dict(width=1, color=INK),
            ),
        )
    )
    fig.update_layout(
        title=f"Траектория в пространстве тем: {fio}",
        xaxis_title=f"PC1 ({explained_var[0] * 100:.1f}% дисперсии)",
        yaxis_title=f"PC2 ({explained_var[1] * 100:.1f}% дисперсии)",
    )
    return _style(fig)


def fig_similarity_heatmap(similarity_matrix, labels, order=None):
    if order is not None:
        similarity_matrix = similarity_matrix[np.ix_(order, order)]
        labels = [labels[i] for i in order]
    fig = go.Figure(
        go.Heatmap(
            z=similarity_matrix, x=labels, y=labels, colorscale=PINK_SCALE,
            colorbar=dict(title="Косинусное сходство"),
        )
    )
    fig.update_layout(title="Матрица тематической близости авторов школы")
    return _style(fig, height=800)


def fig_closest_authors(closest_list):
    names = [x[0] for x in closest_list]
    scores = [x[2] for x in closest_list]
    fig = go.Figure(
        go.Bar(
            x=scores[::-1], y=names[::-1], orientation="h",
            text=[f"{s:.3f}" for s in scores[::-1]], textposition="outside",
            marker_color=PRIMARY,
        )
    )
    fig.update_layout(
        title="Ближайшие по тематике авторы", xaxis_title="Косинусное сходство",
        xaxis_range=[0, 1.05], margin=dict(l=260),
    )
    return _style(fig, height=max(400, len(names) * 26))


def fig_entropy_ranking(results, top_n=None):
    if top_n:
        results = results[:top_n]
    names = [r[0] for r in results]
    values = [r[3] * 100 for r in results]
    fig = go.Figure(
        go.Bar(
            x=values[::-1], y=names[::-1], orientation="h",
            text=[f"{v:.1f}%" for v in values[::-1]], textposition="outside",
            marker_color=PRIMARY,
        )
    )
    fig.update_layout(
        title="Рейтинг разносторонности авторов школы",
        xaxis_title="Нормированная энтропия, %", xaxis_range=[0, 105],
        margin=dict(l=260),
    )
    return _style(fig, height=max(400, len(names) * 26))


def fig_school_topic_top(top_topics, factors_map):
    names = [factors_map.get(tid, tid) for tid, _ in top_topics]
    values = [w * 100 for _, w in top_topics]
    fig = go.Figure(
        go.Bar(
            x=values[::-1], y=names[::-1], orientation="h",
            text=[f"{v:.1f}%" for v in values[::-1]], textposition="outside",
            marker_color=PRIMARY,
        )
    )
    fig.update_layout(
        title=f"Топ-{len(top_topics)} тем школы за весь период",
        xaxis_title="Средняя доля, %", margin=dict(l=260),
    )
    return _style(fig, height=max(400, len(names) * 32))


def fig_school_topic_dynamics(school_by_year, top_topic_ids, factors_map, years):
    fig = go.Figure()
    for tid in top_topic_ids:
        values = [school_by_year[y]["vector"].get(tid, 0) * 100 for y in years]
        fig.add_trace(
            go.Scatter(x=years, y=values, mode="lines+markers", name=factors_map.get(tid, tid))
        )
    fig.update_layout(
        title="Динамика тем школы по годам", xaxis_title="Год",
        yaxis_title="Доля в векторе школы, %",
    )
    return _style(fig)


def fig_topic_trends(trends, factors_map, top_n=None, significance_threshold=0.05):
    sorted_trends = sorted(trends.items(), key=lambda x: -x[1]["slope"])
    if top_n:
        sorted_trends = sorted_trends[:top_n] + sorted_trends[-top_n:]
    names = [factors_map.get(tid, tid) for tid, _ in sorted_trends]
    slopes = [d["slope"] * 100 for _, d in sorted_trends]
    p_values = [d["p_value"] for _, d in sorted_trends]

    colors = []
    for slope, p in zip(slopes, p_values):
        if p < significance_threshold:
            colors.append(PRIMARY_DARK if slope > 0 else "#8C5866")
        else:
            colors.append(MUTED)

    fig = go.Figure(
        go.Bar(
            x=slopes[::-1], y=names[::-1], orientation="h", marker_color=colors[::-1],
            text=[f"{s:.3f}" for s in slopes[::-1]], textposition="outside",
        )
    )
    fig.add_vline(x=0, line_color=INK, line_width=1)
    fig.update_layout(
        title="Тренды тем школы (насыщенный цвет — значимо при p<0.05, приглушённый — незначимо)",
        xaxis_title="Наклон тренда, п.п./год", margin=dict(l=260),
    )
    return _style(fig, height=max(400, len(names) * 26))


def fig_topic_reach(topic_author_count, factors_map, threshold, top_n=None):
    sorted_reach = sorted(topic_author_count.items(), key=lambda x: -x[1])
    if top_n:
        sorted_reach = sorted_reach[:top_n]
    names = [factors_map.get(tid, tid) for tid, _ in sorted_reach]
    counts = [c for _, c in sorted_reach]
    fig = go.Figure(
        go.Bar(
            x=counts[::-1], y=names[::-1], orientation="h", marker_color=PRIMARY,
            text=counts[::-1], textposition="outside",
        )
    )
    fig.update_layout(
        title=f"Ядро vs периферия школы (порог веса: {threshold * 100:.0f}%)",
        xaxis_title="Число авторов, у кого тема значима",
        margin=dict(l=260),
    )
    return _style(fig, height=max(400, len(names) * 26))


def fig_school_activity(school_by_year):
    years = sorted(school_by_year.keys())
    n_authors = [school_by_year[y]["n_authors"] for y in years]
    fig = px.line(x=years, y=n_authors, markers=True, color_discrete_sequence=[PRIMARY])
    fig.update_layout(
        title="Активность школы по годам", xaxis_title="Год",
        yaxis_title="Число авторов с публикациями",
    )
    return _style(fig)


def fig_topic_forecast(years, values, future_years, forecast_values, topic_name, p_value,
                        significance_threshold=0.05):
    significant = p_value < significance_threshold
    note = "тренд статистически значим" if significant else "тренд статистически не значим — прогноз ненадёжен"

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=years, y=values, mode="lines+markers", name="Фактические данные",
            line=dict(color=PRIMARY), marker=dict(size=7),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=future_years, y=forecast_values, mode="lines+markers", name="Прогноз (экстраполяция тренда)",
            line=dict(color=PRIMARY_DARK if significant else MUTED, dash="dash"), marker=dict(size=7),
        )
    )
    fig.add_vline(x=years[-1], line_dash="dot", line_color=MUTED)
    fig.update_layout(
        title=f"{topic_name} — прогноз на {len(future_years) - 1} лет ({note}, p={p_value:.3f})",
        xaxis_title="Год", yaxis_title="Доля, %",
    )
    return _style(fig)
