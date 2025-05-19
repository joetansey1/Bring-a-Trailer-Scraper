from influxdb_client import Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from config import INFLUX_URL, INFLUX_TOKEN, ORG, BUCKET
from influxdb_client import InfluxDBClient

def write_to_influx(**kwargs):
    point = (
        Point("GT350 Price")
        .field("price", float(kwargs.get("price", 0)))
        .tag("year", str(kwargs.get("year", "unknown")))
        .tag("mileage", str(kwargs.get("mileage", "unknown")))
        .tag("color", kwargs.get("color", "unknown"))
        .tag("link", kwargs.get("link", ""))
        .tag("status", kwargs.get("status", ""))
        .tag("source", kwargs.get("source", ""))
    )

    time_value = kwargs.get("time")
    if time_value:
        point.time(time_value, WritePrecision.NS)

    with InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=ORG) as client:
        write_api = client.write_api(write_options=SYNCHRONOUS)
        write_api.write(bucket=BUCKET, org=ORG, record=point)
