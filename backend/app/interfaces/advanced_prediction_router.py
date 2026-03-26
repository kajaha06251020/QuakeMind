"""最先端予測 API ルーター (Tier 1)"""
from typing import Optional
from fastapi import APIRouter, Query
from app.infrastructure import db

router = APIRouter(prefix="/advanced-prediction", tags=["advanced-prediction"])


async def _get_records(region=None, start=None, end=None):
    from datetime import datetime as dt
    start_dt = dt.fromisoformat(start) if start else None
    end_dt = dt.fromisoformat(end) if end else None
    return await db.get_events_as_records(region=region, start=start_dt, end=end_dt)


@router.get("/bayesian-etas")
async def bayesian_etas(
    region: Optional[str] = None, start: Optional[str] = None, end: Optional[str] = None,
    hours: int = Query(default=72, ge=1, le=720),
    n_samples: int = Query(default=200, ge=50, le=2000),
):
    from app.usecases.bayesian_etas import bayesian_etas_forecast
    records = await _get_records(region, start, end)
    return bayesian_etas_forecast(records, forecast_hours=hours, n_samples=n_samples, burn_in=max(50, n_samples // 5))


@router.get("/coulomb-rate-state")
async def coulomb_rs(
    delta_cfs_mpa: float = Query(...),
    background_rate: float = Query(default=0.5),
    forecast_days: float = Query(default=30),
):
    from app.usecases.coulomb_rate_state import rate_state_forecast
    return rate_state_forecast(background_rate, delta_cfs_mpa, forecast_days)


@router.get("/changepoints")
async def changepoints(
    region: Optional[str] = None, start: Optional[str] = None, end: Optional[str] = None,
    window_days: int = Query(default=7, ge=3, le=30),
):
    from app.usecases.changepoint import detect_rate_changepoints
    records = await _get_records(region, start, end)
    return detect_rate_changepoints(records, window_days=window_days)


@router.get("/ensemble")
async def ensemble_predict(
    region: Optional[str] = None, start: Optional[str] = None, end: Optional[str] = None,
):
    """マルチモデルアンサンブル（BMA）予測。"""
    from app.usecases.etas import etas_forecast
    from app.usecases.ml_predictor import predict_large_earthquake
    from app.usecases.ensemble import bayesian_model_averaging

    records = await _get_records(region, start, end)
    if len(records) < 10:
        return {"error": "イベント数不足"}

    etas = etas_forecast(records, forecast_hours=72)
    ml = predict_large_earthquake(records)

    preds = [
        {"name": "etas", "probability": min(1, etas.get("probability_m4_plus", 0)), "weight": 2.0, "uncertainty": 0.15},
        {"name": "ml", "probability": min(1, ml.get("probability", 0)), "weight": 1.0, "uncertainty": 0.2},
    ]
    return bayesian_model_averaging(preds)


@router.get("/oef-forecast")
async def oef_forecast(
    region: Optional[str] = None, start: Optional[str] = None, end: Optional[str] = None,
    magnitude_threshold: float = Query(default=5.0, ge=3.0, le=9.0),
):
    """Operational Earthquake Forecasting — 24h/7d/30d 確率予報。"""
    from app.usecases.oef import generate_oef_forecast
    records = await _get_records(region, start, end)
    return await generate_oef_forecast(records, magnitude_threshold=magnitude_threshold)


@router.get("/fault-interactions")
async def fault_interactions(region: Optional[str] = None, start: Optional[str] = None, end: Optional[str] = None):
    from app.usecases.fault_graph import analyze_fault_interactions
    records = await _get_records(region, start, end)
    return analyze_fault_interactions(records)


@router.post("/analyze-waveform")
async def analyze_waveform_endpoint(data: dict):
    from app.usecases.phase_detection import analyze_waveform
    import numpy as np
    waveform = np.array(data.get("waveform", []))
    sr = data.get("sampling_rate", 100.0)
    if len(waveform) < 100:
        return {"error": "波形データが短すぎます（最低100サンプル）"}
    return analyze_waveform(waveform, sr)


@router.get("/self-improvement")
async def self_improvement_status():
    from app.services.self_improvement import get_improvement_summary
    return get_improvement_summary()


@router.post("/self-improvement/verify")
async def self_improvement_verify(model_name: str, predicted_prob: float, actual_occurred: bool):
    from app.services.self_improvement import verify_and_update
    return await verify_and_update(model_name, predicted_prob, actual_occurred)


@router.get("/domain-similarity")
async def domain_similarity(region: Optional[str] = None):
    from app.usecases.transfer_learning import extract_transfer_features, compute_domain_similarity
    all_records = await _get_records()
    region_records = await _get_records(region=region) if region else all_records
    source = extract_transfer_features(all_records)
    target = extract_transfer_features(region_records)
    return compute_domain_similarity(source, target)


@router.get("/finite-fault")
async def finite_fault(
    magnitude: float = Query(...),
    depth_km: float = Query(default=15.0),
    rake: float = Query(default=90.0),
):
    from app.usecases.finite_fault import estimate_fault_geometry, generate_slip_distribution
    geom = estimate_fault_geometry(magnitude, depth_km, rake)
    slip = generate_slip_distribution(geom["rupture_length_km"], geom["rupture_width_km"], geom["average_slip_m"])
    return {
        "geometry": geom,
        "slip_distribution": {k: v for k, v in slip.items() if k != "slip_grid"},
        "has_slip_grid": True,
    }


@router.post("/stress-inversion")
async def stress_inversion(mechanisms: list[dict]):
    from app.usecases.stress_inversion import invert_stress_field
    return invert_stress_field(mechanisms)


@router.get("/cascade-probability")
async def cascade_prob(
    lat: float = Query(...),
    lon: float = Query(...),
    magnitude: float = Query(...),
):
    from app.usecases.cascade import compute_cascade_probability
    return compute_cascade_probability(lat, lon, magnitude)


@router.get("/rate-state-simulation")
async def rate_state_sim(
    a: float = Query(default=0.01),
    b: float = Query(default=0.015),
    duration_years: float = Query(default=50),
):
    from app.usecases.rate_state_sim import simulate_rate_state
    return simulate_rate_state(a=a, b=b, duration_years=duration_years, dt_years=max(0.1, duration_years / 500))


@router.get("/tectonic-classification")
async def tectonic_classify(
    region: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
):
    from app.usecases.tectonic_classifier import classify_events
    records = await _get_records(region, start, end)
    return classify_events(records)


@router.get("/hazard-map")
async def hazard_map(
    region: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
):
    from app.usecases.hazard_map import compute_hazard_map
    records = await _get_records(region, start, end)
    return compute_hazard_map(records)


@router.get("/sequence-classification")
async def sequence_classify(
    region: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
):
    from app.usecases.sequence_classifier import classify_sequence
    records = await _get_records(region, start, end)
    return classify_sequence(records)


@router.get("/paper-survey")
async def paper_survey(query: str = Query(default="earthquake prediction")):
    from app.services.paper_survey import search_arxiv_papers
    return {"papers": await search_arxiv_papers(query, max_results=5)}


@router.post("/generate-notebook")
async def generate_notebook(region: Optional[str] = None):
    from app.services.notebook_generator import generate_daily_notebook
    from app.services.research_scheduler import daily_analysis
    from fastapi.responses import PlainTextResponse

    analyses = {}
    try:
        analyses = await daily_analysis()
    except Exception:
        pass
    md = generate_daily_notebook(analyses)
    return PlainTextResponse(content=md, media_type="text/markdown")


@router.get("/precursor-fusion")
async def precursor_fusion(signals: str = Query(default="{}")):
    from app.usecases.precursor_fusion import compute_precursor_score
    import json
    return compute_precursor_score(json.loads(signals))


@router.get("/information-theory")
async def info_theory(region: Optional[str] = None, start: Optional[str] = None, end: Optional[str] = None):
    from app.usecases.information_theory import analyze_parameter_dependencies
    import numpy as np
    records = await _get_records(region, start, end)
    if len(records) < 10:
        return {"error": "イベント数不足"}
    mags = np.array([r.magnitude for r in records])
    depths = np.array([r.depth_km for r in records])
    lats = np.array([r.latitude for r in records])
    lons = np.array([r.longitude for r in records])
    return analyze_parameter_dependencies(mags, depths, lats, lons)


@router.get("/seismic-gaps")
async def seismic_gaps(region: Optional[str] = None):
    from app.usecases.seismic_gap import analyze_seismic_gaps
    records = await _get_records(region=region)
    return analyze_seismic_gaps(records)


@router.get("/stress-history")
async def stress_history(lat: float = Query(...), lon: float = Query(...), region: Optional[str] = None):
    from app.usecases.stress_history import compute_cumulative_stress
    records = await _get_records(region=region)
    return compute_cumulative_stress(records, lat, lon)


@router.get("/topological-analysis")
async def topo_analysis(region: Optional[str] = None, start: Optional[str] = None, end: Optional[str] = None):
    from app.usecases.tda import compute_persistence
    records = await _get_records(region, start, end)
    return compute_persistence(records)


@router.post("/generate-hypotheses")
async def gen_hypotheses(analysis_results: dict):
    from app.services.llm_hypothesis import generate_hypotheses_from_analysis
    return {"hypotheses": await generate_hypotheses_from_analysis(analysis_results)}


@router.post("/causal-test")
async def causal_test(x: list[float], y: list[float], max_lag: int = 5):
    from app.usecases.causal_inference import bidirectional_causality
    import numpy as np
    return bidirectional_causality(np.array(x), np.array(y), max_lag)


@router.get("/counterfactual")
async def counterfactual(event_id: str = Query(...), region: Optional[str] = None, hours: int = Query(default=72)):
    from app.usecases.counterfactual import counterfactual_analysis
    records = await _get_records(region=region)
    return counterfactual_analysis(records, event_id, hours)


@router.get("/data-gaps")
async def data_gaps(region: Optional[str] = None):
    from app.services.active_learning import identify_data_gaps
    records = await _get_records(region=region)
    return identify_data_gaps(records)


@router.get("/uncertainty-map")
async def uncertainty_map():
    from app.services.active_learning import compute_model_uncertainty_map
    records = await _get_records()
    return compute_model_uncertainty_map(records)


@router.get("/explain")
async def explain(region: Optional[str] = None, start: Optional[str] = None, end: Optional[str] = None):
    from app.usecases.explainability import explain_prediction
    records = await _get_records(region, start, end)
    return explain_prediction(records, n_permutations=5)


@router.get("/model-scoreboard")
async def model_scoreboard():
    from app.services.model_scoreboard import get_scoreboard
    return get_scoreboard()


@router.get("/knowledge-gaps")
async def knowledge_gaps_endpoint(region: Optional[str] = None):
    from app.services.knowledge_gaps import detect_knowledge_gaps
    records = await _get_records(region=region)
    return detect_knowledge_gaps(records)


@router.get("/research-strategy")
async def research_strategy(region: Optional[str] = None):
    from app.services.knowledge_gaps import detect_knowledge_gaps
    from app.services.model_scoreboard import get_scoreboard
    from app.services.research_strategy import recommend_research_strategy
    records = await _get_records(region=region)
    gaps = detect_knowledge_gaps(records)
    scoreboard = get_scoreboard()
    return recommend_research_strategy(gaps, model_scoreboard=scoreboard)


@router.get("/stress-tomography")
async def stress_tomography(region: Optional[str] = None, start: Optional[str] = None, end: Optional[str] = None):
    from app.usecases.stress_tomography import compute_3d_stress_field
    records = await _get_records(region, start, end)
    return compute_3d_stress_field(records, grid_spacing_deg=1.0, depth_layers=[15, 30, 50])


@router.get("/rupture-simulation")
async def rupture_sim(segment_id: str = Query(...), magnitude: float = Query(default=8.0), n_simulations: int = Query(default=500)):
    from app.usecases.rupture_propagation import simulate_rupture
    return simulate_rupture(segment_id, magnitude, n_simulations)


@router.get("/multiscale-analysis")
async def multiscale(region: Optional[str] = None, start: Optional[str] = None, end: Optional[str] = None):
    from app.usecases.multiscale import multiscale_analysis
    records = await _get_records(region, start, end)
    return multiscale_analysis(records)


@router.get("/criticality-index")
async def criticality(region: Optional[str] = None, start: Optional[str] = None, end: Optional[str] = None):
    from app.usecases.criticality import compute_criticality_index
    records = await _get_records(region, start, end)
    return compute_criticality_index(records)


@router.get("/meta-cognition")
async def meta_cognition(region: Optional[str] = None):
    from app.services.meta_cognition import self_evaluate
    records = await _get_records(region=region)
    return await self_evaluate(records)


@router.get("/adversarial-test")
async def adversarial(region: Optional[str] = None, start: Optional[str] = None, end: Optional[str] = None):
    from app.services.adversarial_testing import adversarial_test
    records = await _get_records(region, start, end)
    return adversarial_test(records)


@router.get("/emergent-patterns")
async def emergent(region: Optional[str] = None, start: Optional[str] = None, end: Optional[str] = None):
    from app.usecases.emergent_patterns import detect_emergent_patterns
    records = await _get_records(region, start, end)
    return detect_emergent_patterns(records)


@router.get("/surprise")
async def surprise(region: Optional[str] = None, start: Optional[str] = None, end: Optional[str] = None):
    from app.usecases.predictive_coding import compute_surprise
    records = await _get_records(region, start, end)
    return compute_surprise(records)


@router.get("/renormalization")
async def renorm(region: Optional[str] = None, start: Optional[str] = None, end: Optional[str] = None):
    from app.usecases.renormalization import renormalization_analysis
    records = await _get_records(region, start, end)
    return renormalization_analysis(records)


@router.get("/distribution-change")
async def dist_change(region: Optional[str] = None, start: Optional[str] = None, end: Optional[str] = None):
    from app.usecases.info_geometry import compute_distribution_change
    import numpy as np
    records = await _get_records(region, start, end)
    if len(records) < 20:
        return {"error": "イベント数不足"}
    mags = np.array([r.magnitude for r in records])
    return compute_distribution_change(mags)


@router.get("/max-entropy")
async def max_ent(region: Optional[str] = None, start: Optional[str] = None, end: Optional[str] = None):
    from app.usecases.max_entropy import max_entropy_rate
    import numpy as np
    from collections import Counter
    from datetime import datetime as dt, timedelta, timezone as tz
    records = await _get_records(region, start, end)
    if len(records) < 10:
        return {"error": "イベント数不足"}

    def _ts(e):
        try:
            return dt.fromisoformat(e.timestamp.replace("Z", "+00:00"))
        except Exception:
            return dt(2000, 1, 1, tzinfo=tz.utc)

    timestamps = [_ts(e) for e in records]
    daily = Counter(t.date() for t in timestamps)
    counts = list(daily.values())
    return max_entropy_rate(float(np.mean(counts)), float(np.var(counts)))


@router.get("/state-space")
async def state_sp(region: Optional[str] = None, start: Optional[str] = None, end: Optional[str] = None):
    from app.usecases.state_space import kalman_stress_filter
    import numpy as np
    from collections import Counter
    from datetime import datetime as dt, timedelta, timezone as tz
    records = await _get_records(region, start, end)
    if len(records) < 10:
        return {"error": "イベント数不足"}

    def _ts(e):
        try:
            return dt.fromisoformat(e.timestamp.replace("Z", "+00:00"))
        except Exception:
            return dt(2000, 1, 1, tzinfo=tz.utc)

    timestamps = sorted([_ts(e) for e in records])
    first = timestamps[0].date()
    last = timestamps[-1].date()
    daily = Counter(t.date() for t in timestamps)
    n_days = (last - first).days + 1
    counts = [float(daily.get(first + timedelta(days=d), 0)) for d in range(n_days)]
    return kalman_stress_filter(counts)


@router.get("/digital-twin")
async def digital_twin(region: Optional[str] = None):
    from app.usecases.fault_digital_twin import compute_digital_twin
    records = await _get_records(region=region)
    return compute_digital_twin(records)


@router.get("/optimal-observation")
async def optimal_obs(region: Optional[str] = None, n: int = Query(default=3, ge=1, le=8)):
    from app.usecases.optimal_observation import recommend_observation_sites
    records = await _get_records(region=region)
    return recommend_observation_sites(records, n)


@router.get("/rupture-arrest")
async def rupture_arrest(length_km: float = Query(default=100), width_km: float = Query(default=30), heterogeneity: float = Query(default=0.3), n_sims: int = Query(default=200)):
    from app.usecases.rupture_arrest import simulate_rupture_arrest
    return simulate_rupture_arrest(length_km, width_km, n_simulations=n_sims, heterogeneity=heterogeneity)

@router.get("/slow-slip")
async def slow_slip(region: Optional[str] = None, start: Optional[str] = None, end: Optional[str] = None):
    from app.usecases.slow_slip import detect_slow_slip_correlation
    records = await _get_records(region, start, end)
    return detect_slow_slip_correlation(records)

@router.post("/fluid-correlation")
async def fluid_corr(data: dict):
    from app.usecases.fluid_correlation import correlate_fluid_signals
    import numpy as np
    eq = np.array(data.get("earthquake_counts", []))
    rain = np.array(data["precipitation_mm"]) if "precipitation_mm" in data else None
    tidal = np.array(data["tidal_force"]) if "tidal_force" in data else None
    return correlate_fluid_signals(eq, precipitation_mm=rain, tidal_force=tidal)

@router.post("/lyapunov")
async def lyapunov(data: dict):
    from app.usecases.lyapunov import estimate_lyapunov
    import numpy as np
    ts = np.array(data.get("timeseries", []))
    return estimate_lyapunov(ts, embedding_dim=data.get("embedding_dim", 3))

@router.get("/deep-earthquake-mechanism")
async def deep_eq(depth_km: float = Query(...), magnitude: float = Query(...)):
    from app.usecases.deep_earthquake import classify_deep_mechanism
    return classify_deep_mechanism(depth_km, magnitude)


@router.get("/site-amplification")
async def site_amp(base_intensity: float = Query(...), vs30: float = Query(default=180)):
    from app.usecases.site_amplification import compute_site_amplification
    return compute_site_amplification(base_intensity, vs30)


@router.get("/multi-gmpe")
async def multi_gmpe(magnitude: float = Query(...), distance_km: float = Query(...), depth_km: float = Query(default=10)):
    from app.usecases.multi_gmpe import evaluate_multi_gmpe
    return evaluate_multi_gmpe(magnitude, distance_km, depth_km)


@router.get("/spatial-bvalue")
async def spatial_bval(region: Optional[str] = None, start: Optional[str] = None, end: Optional[str] = None):
    from app.usecases.spatial_bvalue import compute_spatial_bvalue
    records = await _get_records(region, start, end)
    return compute_spatial_bvalue(records)


@router.get("/moment-rate")
async def moment_rate(region: Optional[str] = None, start: Optional[str] = None, end: Optional[str] = None):
    from app.usecases.moment_rate import compute_moment_rate
    records = await _get_records(region, start, end)
    return compute_moment_rate(records)


@router.get("/magnitude-convert")
async def mag_convert(magnitude: float = Query(...), scale: str = Query(default="ML")):
    from app.usecases.magnitude_conversion import convert_to_mw
    return convert_to_mw(magnitude, scale)


@router.get("/repeating-earthquakes")
async def repeaters(region: Optional[str] = None, start: Optional[str] = None, end: Optional[str] = None):
    from app.usecases.repeating_earthquakes import detect_repeaters
    records = await _get_records(region, start, end)
    return detect_repeaters(records)


@router.get("/doublets")
async def doublets(region: Optional[str] = None, start: Optional[str] = None, end: Optional[str] = None):
    from app.usecases.doublet_detection import detect_doublets
    records = await _get_records(region, start, end)
    return detect_doublets(records)


@router.get("/interevent-time")
async def interevent(region: Optional[str] = None, start: Optional[str] = None, end: Optional[str] = None):
    from app.usecases.interevent_time import analyze_interevent_times
    records = await _get_records(region, start, end)
    return analyze_interevent_times(records)


@router.post("/csep-comparison")
async def csep(predictions: list[dict]):
    from app.usecases.model_comparison import csep_comparison
    return csep_comparison(predictions)


@router.get("/aftershock-hazard")
async def aftershock_haz(lat: float = Query(...), lon: float = Query(...), region: Optional[str] = None, hours: int = Query(default=72)):
    from app.usecases.aftershock_hazard import compute_aftershock_hazard
    records = await _get_records(region=region)
    return compute_aftershock_hazard(records, lat, lon, hours)


@router.get("/tsunami-simulation")
async def tsunami_sim(lat: float = Query(...), lon: float = Query(...), magnitude: float = Query(...), depth_km: float = Query(default=15)):
    from app.usecases.tsunami_simulation import simulate_tsunami_propagation
    return simulate_tsunami_propagation(lat, lon, magnitude, depth_km, grid_size=30, total_minutes=30)


@router.get("/early-warning")
async def eew(p_amplitude: float = Query(...), p_period: float = Query(...), distance_km: float = Query(default=100)):
    from app.usecases.early_warning import estimate_from_p_wave
    return estimate_from_p_wave(p_amplitude, p_period, distance_km)


@router.get("/stress-drop")
async def stress_drop_endpoint(magnitude: float = Query(...)):
    from app.usecases.stress_drop import estimate_stress_drop
    return estimate_stress_drop(magnitude)


@router.get("/tidal-triggering")
async def tidal(region: Optional[str] = None, start: Optional[str] = None, end: Optional[str] = None):
    from app.usecases.tidal_triggering import schuster_test
    records = await _get_records(region, start, end)
    return schuster_test(records)


@router.get("/mc-map")
async def mc_map(region: Optional[str] = None, start: Optional[str] = None, end: Optional[str] = None):
    from app.usecases.mc_mapping import compute_mc_map
    records = await _get_records(region, start, end)
    return compute_mc_map(records)


@router.get("/nowcast")
async def nowcast_endpoint(region: Optional[str] = None):
    from app.usecases.nowcasting import nowcast
    records = await _get_records(region=region)
    return nowcast(records)


@router.get("/energy-partition")
async def energy(region: Optional[str] = None, start: Optional[str] = None, end: Optional[str] = None):
    from app.usecases.energy_partition import analyze_energy_partition
    records = await _get_records(region, start, end)
    return analyze_energy_partition([r.magnitude for r in records])


@router.get("/source-spectrum")
async def spectrum(magnitude: float = Query(...)):
    from app.usecases.source_spectrum import fit_brune_spectrum
    return fit_brune_spectrum(magnitude)


@router.get("/volcano-seismic")
async def volcano(region: Optional[str] = None):
    from app.usecases.volcano_seismic import analyze_volcano_seismic
    records = await _get_records(region=region)
    return analyze_volcano_seismic(records)


@router.get("/ambient-noise")
async def ambient():
    from app.usecases.ambient_noise import detect_velocity_change
    return detect_velocity_change()
