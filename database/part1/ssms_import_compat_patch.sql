-- Run this in the IOT_Control database if the tables were already created
-- from an older schema.sql before the SSMS import compatibility changes.

IF OBJECT_ID('dbo.node_info', 'U') IS NOT NULL
BEGIN
    ALTER TABLE dbo.node_info ALTER COLUMN max_depth NVARCHAR(64) NULL;
    ALTER TABLE dbo.node_info ALTER COLUMN initial_depth NVARCHAR(64) NULL;
    ALTER TABLE dbo.node_info ALTER COLUMN surcharge_depth NVARCHAR(64) NULL;
    ALTER TABLE dbo.node_info ALTER COLUMN ponded_area NVARCHAR(64) NULL;
    ALTER TABLE dbo.node_info ALTER COLUMN is_storage NVARCHAR(8) NULL;
    ALTER TABLE dbo.node_info ALTER COLUMN is_outfall NVARCHAR(8) NULL;
    ALTER TABLE dbo.node_info ALTER COLUMN is_pump_station_forebay NVARCHAR(8) NULL;
END;

IF OBJECT_ID('dbo.conduit_info', 'U') IS NOT NULL
BEGIN
    ALTER TABLE dbo.conduit_info ALTER COLUMN minor_loss_inlet NVARCHAR(64) NULL;
    ALTER TABLE dbo.conduit_info ALTER COLUMN minor_loss_outlet NVARCHAR(64) NULL;
    ALTER TABLE dbo.conduit_info ALTER COLUMN minor_loss_average NVARCHAR(64) NULL;
END;

IF OBJECT_ID('dbo.pump_info', 'U') IS NOT NULL
BEGIN
    ALTER TABLE dbo.pump_info ALTER COLUMN is_parallel_pump NVARCHAR(8) NULL;
END;

IF OBJECT_ID('dbo.facility_info', 'U') IS NOT NULL
BEGIN
    ALTER TABLE dbo.facility_info ALTER COLUMN crest_height NVARCHAR(64) NULL;
    ALTER TABLE dbo.facility_info ALTER COLUMN discharge_coefficient NVARCHAR(64) NULL;
END;

IF OBJECT_ID('dbo.pump_operation_timeseries', 'U') IS NOT NULL
BEGIN
    ALTER TABLE dbo.pump_operation_timeseries ALTER COLUMN is_startup NVARCHAR(8) NULL;
    ALTER TABLE dbo.pump_operation_timeseries ALTER COLUMN is_shutdown NVARCHAR(8) NULL;
END;
