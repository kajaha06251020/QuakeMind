"""LangGraph グラフ定義: predict → route → personal の処理パイプライン。"""
from langgraph.graph import StateGraph, END

from state import EventState
from agents.predict import predict_node
from agents.route import route_node
from agents.personal import personal_node


def build_graph():
    """EventState を流れる LangGraph グラフを構築して返す。"""
    builder = StateGraph(EventState)

    builder.add_node("predict", predict_node)
    builder.add_node("route", route_node)
    builder.add_node("personal", personal_node)

    builder.set_entry_point("predict")
    builder.add_edge("predict", "route")
    builder.add_edge("route", "personal")
    builder.add_edge("personal", END)

    return builder.compile()


# アプリ起動時に一度だけ生成する
graph = build_graph()
