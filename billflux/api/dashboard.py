"""Endpoints do dashboard (relatórios) da API JSON."""

from flask import request

from billflux.api import bp, api_login_required, api_response
from billflux.controlers.home import _dashboard_context


def _serialize_period(period):
    return {
        "key": period["key"],
        "start": period["start"].isoformat(),
        "end": period["end"].isoformat(),
        "date": period["date"],
        "label": period["label"],
    }


@bp.route("/dashboard")
@api_login_required
def dashboard():
    """Métricas, série diária, contas em aberto e últimas vendas do período."""
    context = _dashboard_context(request.args)

    return api_response(
        {
            "period": _serialize_period(context["period"]),
            "metrics": {
                "faturamento": float(context["metrics"]["faturamento"]),
                "vendas": context["metrics"]["vendas"],
                "ticket": float(context["metrics"]["ticket"]),
                "lucro": float(context["metrics"]["lucro"]),
            },
            "series": [
                {
                    "label": item["label"],
                    "value": float(item["value"]),
                    "date": item["date"].isoformat(),
                }
                for item in context["series"]
            ],
            "chart_max": float(context["chart_max"]),
            "open_bills": [
                {
                    "reference": bill.reference,
                    "due_date": bill.due_date.isoformat(),
                    "value": float(bill.value),
                }
                for bill in context["open_bills"]
            ],
            "recent_sales": [
                {
                    "date": item["date"].isoformat(),
                    "source": item["source"],
                    "value": float(item["value"]),
                }
                for item in context["recent_sales"]
            ],
        }
    )
