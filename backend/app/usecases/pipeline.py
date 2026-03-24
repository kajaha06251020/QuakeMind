"""LangGraph グラフ定義: predict → route → personal。"""
from langgraph.graph import StateGraph, END

from app.domain.models import EventState
from app.usecases.predict import predict_node
from app.usecases.route import route_node
from app.usecases.personal import personal_node


def build_graph():
    builder = StateGraph(EventState)
    builder.add_node("predict", predict_node)
    builder.add_node("route", route_node)
    builder.add_node("personal", personal_node)
    builder.set_entry_point("predict")
    builder.add_edge("predict", "route")
    builder.add_edge("route", "personal")
    builder.add_edge("personal", END)
    return builder.compile()


graph = build_graph()
