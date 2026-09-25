CREATE TABLE IF NOT EXISTS locations (
  location_id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  region TEXT NOT NULL DEFAULT 'Delhi NCR',
  latitude DOUBLE PRECISION,
  longitude DOUBLE PRECISION,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS stations (
  station_id TEXT PRIMARY KEY,
  location_id TEXT REFERENCES locations(location_id),
  name TEXT NOT NULL,
  latitude DOUBLE PRECISION NOT NULL,
  longitude DOUBLE PRECISION NOT NULL,
  zone TEXT,
  source_id TEXT,
  active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS data_sources (
  source_id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  source_type TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'unknown',
  last_success_at TIMESTAMPTZ,
  last_error TEXT
);

CREATE TABLE IF NOT EXISTS air_quality_observations (
  observation_id BIGSERIAL PRIMARY KEY,
  station_id TEXT NOT NULL REFERENCES stations(station_id),
  observed_at TIMESTAMPTZ NOT NULL,
  source TEXT NOT NULL REFERENCES data_sources(source_id),
  pm25 DOUBLE PRECISION, pm10 DOUBLE PRECISION, no2 DOUBLE PRECISION,
  so2 DOUBLE PRECISION, co DOUBLE PRECISION, o3 DOUBLE PRECISION, aqi DOUBLE PRECISION,
  raw_payload JSONB,
  UNIQUE (station_id, observed_at, source)
);

CREATE TABLE IF NOT EXISTS weather_observations (
  observation_id BIGSERIAL PRIMARY KEY,
  latitude DOUBLE PRECISION NOT NULL, longitude DOUBLE PRECISION NOT NULL,
  observed_at TIMESTAMPTZ NOT NULL,
  source TEXT NOT NULL REFERENCES data_sources(source_id),
  temperature_2m DOUBLE PRECISION, relative_humidity_2m DOUBLE PRECISION,
  dew_point_2m DOUBLE PRECISION, surface_pressure DOUBLE PRECISION,
  wind_speed_10m DOUBLE PRECISION, wind_direction_10m DOUBLE PRECISION,
  wind_gusts_10m DOUBLE PRECISION, boundary_layer_height DOUBLE PRECISION,
  precipitation DOUBLE PRECISION,
  UNIQUE (latitude, longitude, observed_at, source)
);

CREATE TABLE IF NOT EXISTS engineered_features (
  feature_id BIGSERIAL PRIMARY KEY, station_id TEXT REFERENCES stations(station_id),
  observed_at TIMESTAMPTZ NOT NULL, feature_version TEXT NOT NULL, payload JSONB NOT NULL
);
CREATE TABLE IF NOT EXISTS model_versions (
  model_version TEXT PRIMARY KEY, model_name TEXT NOT NULL, target TEXT NOT NULL,
  trained_at TIMESTAMPTZ, model_path TEXT, status TEXT NOT NULL DEFAULT 'development'
);
CREATE TABLE IF NOT EXISTS model_metrics (
  metric_id BIGSERIAL PRIMARY KEY,
  model_version TEXT NOT NULL REFERENCES model_versions(model_version),
  horizon_hours INTEGER NOT NULL, metrics JSONB NOT NULL
);
CREATE TABLE IF NOT EXISTS forecasts (
  forecast_id BIGSERIAL PRIMARY KEY, station_id TEXT REFERENCES stations(station_id),
  model_version TEXT REFERENCES model_versions(model_version), generated_at TIMESTAMPTZ NOT NULL,
  forecast_at TIMESTAMPTZ NOT NULL, horizon_hours INTEGER NOT NULL,
  payload JSONB NOT NULL
);
CREATE TABLE IF NOT EXISTS alerts (
  alert_id BIGSERIAL PRIMARY KEY, station_id TEXT REFERENCES stations(station_id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(), severity TEXT NOT NULL,
  rule TEXT NOT NULL, message TEXT NOT NULL, evidence JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_aqi_station_time ON air_quality_observations (station_id, observed_at DESC);
CREATE INDEX IF NOT EXISTS idx_weather_location_time ON weather_observations (latitude, longitude, observed_at DESC);
CREATE INDEX IF NOT EXISTS idx_features_station_time ON engineered_features (station_id, observed_at DESC);
CREATE INDEX IF NOT EXISTS idx_forecasts_station_time ON forecasts (station_id, generated_at DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_created ON alerts (created_at DESC);

INSERT INTO locations (location_id, name) VALUES
  ('delhi', 'Delhi'), ('noida', 'Noida'), ('ghaziabad', 'Ghaziabad'),
  ('gurugram', 'Gurugram'), ('faridabad', 'Faridabad')
ON CONFLICT (location_id) DO NOTHING;

INSERT INTO data_sources (source_id, name, source_type) VALUES
  ('openaq', 'OpenAQ v3', 'air_quality'), ('open_meteo', 'Open-Meteo', 'weather')
ON CONFLICT (source_id) DO NOTHING;
