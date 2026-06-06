IF OBJECT_ID('rainfall_observed', 'U') IS NOT NULL DROP TABLE rainfall_observed;
CREATE TABLE rainfall_observed (
    timestamp DATETIME2 NOT NULL,
    rain_gage_id NVARCHAR(64) NOT NULL,
    rainfall_mm FLOAT NULL,
    time_interval_min INT NULL,
    source_file NVARCHAR(255) NULL
);
CREATE INDEX IX_rainfall_observed_timestamp ON rainfall_observed(timestamp);

IF OBJECT_ID('rainfall_forecast_scenario', 'U') IS NOT NULL DROP TABLE rainfall_forecast_scenario;
CREATE TABLE rainfall_forecast_scenario (
    forecast_time DATETIME2 NOT NULL,
    target_time DATETIME2 NOT NULL,
    rain_gage_id NVARCHAR(64) NOT NULL,
    forecast_horizon_min INT NULL,
    forecast_rainfall_mm FLOAT NULL,
    source NVARCHAR(128) NULL
);
CREATE INDEX IX_rainfall_forecast_target_time ON rainfall_forecast_scenario(target_time);

IF OBJECT_ID('node_info', 'U') IS NOT NULL DROP TABLE node_info;
CREATE TABLE node_info (
    node_id NVARCHAR(128) NOT NULL PRIMARY KEY,
    node_type NVARCHAR(32) NULL,
    invert_elevation FLOAT NULL,
    max_depth NVARCHAR(64) NULL,
    initial_depth NVARCHAR(64) NULL,
    surcharge_depth NVARCHAR(64) NULL,
    ponded_area NVARCHAR(64) NULL,
    x_coord FLOAT NULL,
    y_coord FLOAT NULL,
    is_storage NVARCHAR(8) NULL,
    is_outfall NVARCHAR(8) NULL,
    is_pump_station_forebay NVARCHAR(8) NULL,
    model_version NVARCHAR(32) NULL,
    is_added BIT NULL
);
CREATE INDEX IX_node_info_node_id ON node_info(node_id);

IF OBJECT_ID('conduit_info', 'U') IS NOT NULL DROP TABLE conduit_info;
CREATE TABLE conduit_info (
    link_id NVARCHAR(128) NOT NULL PRIMARY KEY,
    link_type NVARCHAR(32) NULL,
    inlet_node NVARCHAR(128) NULL,
    outlet_node NVARCHAR(128) NULL,
    length FLOAT NULL,
    roughness FLOAT NULL,
    shape NVARCHAR(64) NULL,
    max_depth_or_diameter FLOAT NULL,
    inlet_offset FLOAT NULL,
    outlet_offset FLOAT NULL,
    slope FLOAT NULL,
    minor_loss_inlet NVARCHAR(64) NULL,
    minor_loss_outlet NVARCHAR(64) NULL,
    minor_loss_average NVARCHAR(64) NULL,
    model_version NVARCHAR(32) NULL,
    is_added BIT NULL
);

IF OBJECT_ID('pump_info', 'U') IS NOT NULL DROP TABLE pump_info;
CREATE TABLE pump_info (
    pump_id NVARCHAR(128) NOT NULL PRIMARY KEY,
    pump_station_id NVARCHAR(128) NULL,
    inlet_node NVARCHAR(128) NULL,
    outlet_node NVARCHAR(128) NULL,
    pump_curve NVARCHAR(128) NULL,
    initial_status NVARCHAR(32) NULL,
    startup_depth FLOAT NULL,
    shutoff_depth FLOAT NULL,
    is_parallel_pump NVARCHAR(8) NULL,
    curve_points NVARCHAR(MAX) NULL,
    model_version NVARCHAR(32) NULL,
    is_added BIT NULL
);
CREATE INDEX IX_pump_info_pump_id ON pump_info(pump_id);
CREATE INDEX IX_pump_info_pump_station_id ON pump_info(pump_station_id);

IF OBJECT_ID('facility_info', 'U') IS NOT NULL DROP TABLE facility_info;
CREATE TABLE facility_info (
    facility_id NVARCHAR(128) NOT NULL,
    facility_type NVARCHAR(64) NULL,
    inlet_node NVARCHAR(128) NULL,
    outlet_node NVARCHAR(128) NULL,
    crest_height NVARCHAR(64) NULL,
    discharge_coefficient NVARCHAR(64) NULL,
    initial_setting NVARCHAR(64) NULL,
    curve_or_rating NVARCHAR(255) NULL,
    model_version NVARCHAR(32) NULL,
    is_added BIT NULL
);
CREATE INDEX IX_facility_info_facility_id ON facility_info(facility_id);

IF OBJECT_ID('subcatchment_info', 'U') IS NOT NULL DROP TABLE subcatchment_info;
CREATE TABLE subcatchment_info (
    subcatchment_id NVARCHAR(128) NOT NULL PRIMARY KEY,
    rain_gage_id NVARCHAR(64) NULL,
    outlet_node NVARCHAR(128) NULL,
    area FLOAT NULL,
    impervious_percent FLOAT NULL,
    width FLOAT NULL,
    slope FLOAT NULL,
    curb_length FLOAT NULL,
    snow_pack NVARCHAR(128) NULL,
    polygon_points NVARCHAR(MAX) NULL,
    subarea_params NVARCHAR(MAX) NULL,
    infiltration_params NVARCHAR(MAX) NULL,
    model_version NVARCHAR(32) NULL,
    is_added BIT NULL
);

IF OBJECT_ID('node_level_timeseries', 'U') IS NOT NULL DROP TABLE node_level_timeseries;
CREATE TABLE node_level_timeseries (
    timestamp DATETIME2 NOT NULL,
    node_id NVARCHAR(128) NOT NULL,
    node_type NVARCHAR(32) NULL,
    depth_m_avg FLOAT NULL,
    depth_m_max FLOAT NULL,
    head_m_avg FLOAT NULL,
    head_m_max FLOAT NULL,
    flooding_cms_instant FLOAT NULL,
    flooding_cms_max_15min FLOAT NULL,
    flooding_volume_m3_15min FLOAT NULL,
    total_inflow_cms_avg FLOAT NULL,
    total_inflow_cms_max FLOAT NULL,
    risk_level NVARCHAR(16) NULL
);
CREATE INDEX IX_node_level_timestamp ON node_level_timeseries(timestamp);
CREATE INDEX IX_node_level_node_id ON node_level_timeseries(node_id);

IF OBJECT_ID('pump_station_level_timeseries', 'U') IS NOT NULL DROP TABLE pump_station_level_timeseries;
CREATE TABLE pump_station_level_timeseries (
    timestamp DATETIME2 NOT NULL,
    pump_station_id NVARCHAR(128) NOT NULL,
    forebay_node NVARCHAR(128) NULL,
    depth_m FLOAT NULL,
    head_m FLOAT NULL,
    percent_full FLOAT NULL,
    level_change_rate_m_per_min FLOAT NULL
);
CREATE INDEX IX_pump_station_level_timestamp ON pump_station_level_timeseries(timestamp);
CREATE INDEX IX_pump_station_level_station_id ON pump_station_level_timeseries(pump_station_id);

IF OBJECT_ID('pump_energy_timeseries', 'U') IS NOT NULL DROP TABLE pump_energy_timeseries;
CREATE TABLE pump_energy_timeseries (
    timestamp DATETIME2 NOT NULL,
    pump_id NVARCHAR(128) NOT NULL,
    pump_station_id NVARCHAR(128) NULL,
    flow_cms_avg FLOAT NULL,
    flow_cms_max FLOAT NULL,
    inlet_head_m_avg FLOAT NULL,
    outlet_head_m_avg FLOAT NULL,
    pump_head_m FLOAT NULL,
    head_source NVARCHAR(64) NULL,
    estimated_power_kw_avg FLOAT NULL,
    energy_kwh_interval FLOAT NULL,
    cumulative_energy_kwh FLOAT NULL,
    unit_energy_kwh_per_kt FLOAT NULL
);
CREATE INDEX IX_pump_energy_timestamp ON pump_energy_timeseries(timestamp);
CREATE INDEX IX_pump_energy_pump_id ON pump_energy_timeseries(pump_id);
CREATE INDEX IX_pump_energy_station_id ON pump_energy_timeseries(pump_station_id);

IF OBJECT_ID('pump_operation_timeseries', 'U') IS NOT NULL DROP TABLE pump_operation_timeseries;
CREATE TABLE pump_operation_timeseries (
    timestamp DATETIME2 NOT NULL,
    pump_id NVARCHAR(128) NOT NULL,
    pump_station_id NVARCHAR(128) NULL,
    flow_cms_avg FLOAT NULL,
    flow_cms_max FLOAT NULL,
    setting_avg FLOAT NULL,
    status NVARCHAR(20) NULL,
    on_seconds_15min FLOAT NULL,
    is_startup NVARCHAR(8) NULL,
    is_shutdown NVARCHAR(8) NULL,
    startup_count_15min INT NULL,
    runtime_min_cumulative FLOAT NULL,
    startup_count_cumulative INT NULL
);
CREATE INDEX IX_pump_operation_timestamp ON pump_operation_timeseries(timestamp);
CREATE INDEX IX_pump_operation_pump_id ON pump_operation_timeseries(pump_id);
CREATE INDEX IX_pump_operation_station_id ON pump_operation_timeseries(pump_station_id);

IF OBJECT_ID('gate_operation_timeseries', 'U') IS NOT NULL DROP TABLE gate_operation_timeseries;
CREATE TABLE gate_operation_timeseries (
    timestamp DATETIME2 NOT NULL,
    gate_id NVARCHAR(128) NOT NULL,
    facility_type NVARCHAR(64) NULL,
    inlet_node NVARCHAR(128) NULL,
    outlet_node NVARCHAR(128) NULL,
    status NVARCHAR(32) NULL,
    setting FLOAT NULL,
    flow_cms FLOAT NULL
);
CREATE INDEX IX_gate_operation_timestamp ON gate_operation_timeseries(timestamp);
CREATE INDEX IX_gate_operation_gate_id ON gate_operation_timeseries(gate_id);

IF OBJECT_ID('raw_node_timeseries', 'U') IS NOT NULL DROP TABLE raw_node_timeseries;
CREATE TABLE raw_node_timeseries (
    timestamp DATETIME2 NOT NULL,
    node_id NVARCHAR(100) NOT NULL,
    node_type NVARCHAR(20) NULL,
    depth_m FLOAT NULL,
    head_m FLOAT NULL,
    flooding_cms FLOAT NULL,
    total_inflow_cms FLOAT NULL
);
CREATE INDEX IX_raw_node_timestamp ON raw_node_timeseries(timestamp);
CREATE INDEX IX_raw_node_node_id ON raw_node_timeseries(node_id);

IF OBJECT_ID('raw_pump_timeseries', 'U') IS NOT NULL DROP TABLE raw_pump_timeseries;
CREATE TABLE raw_pump_timeseries (
    timestamp DATETIME2 NOT NULL,
    pump_id NVARCHAR(100) NOT NULL,
    pump_station_id NVARCHAR(100) NULL,
    flow_cms FLOAT NULL,
    setting FLOAT NULL,
    status NVARCHAR(20) NULL,
    inlet_node NVARCHAR(100) NULL,
    outlet_node NVARCHAR(100) NULL
);
CREATE INDEX IX_raw_pump_timestamp ON raw_pump_timeseries(timestamp);
CREATE INDEX IX_raw_pump_pump_id ON raw_pump_timeseries(pump_id);

IF OBJECT_ID('raw_link_timeseries', 'U') IS NOT NULL DROP TABLE raw_link_timeseries;
CREATE TABLE raw_link_timeseries (
    timestamp DATETIME2 NOT NULL,
    link_id NVARCHAR(100) NOT NULL,
    link_type NVARCHAR(20) NULL,
    flow_cms FLOAT NULL,
    depth_m FLOAT NULL,
    setting FLOAT NULL
);
CREATE INDEX IX_raw_link_timestamp ON raw_link_timeseries(timestamp);
