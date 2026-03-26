import json
from datetime import datetime
import structlog

logger = structlog.get_logger()


class AWSAdapter:
    def __init__(self, client_id: str, config: dict):
        if not client_id:
            raise ValueError("client_id is mandatory")
        self.client_id = client_id
        self.config = config
    
    async def fetch_logs(self) -> list:
        region = self.config.get("region", "us-east-1")
        
        try:
            import boto3
            
            ec2 = boto3.client("ec2", region_name=region)
            cloudwatch = boto3.client("cloudwatch", region_name=region)
            
            logs = []
            
            instances = ec2.describe_instances()
            for reservation in instances.get("Reservations", []):
                for instance in reservation.get("Instances", []):
                    logs.append({
                        "timestamp": datetime.utcnow().isoformat(),
                        "type": "ec2_instance",
                        "data": instance
                    })
            
            alarms = cloudwatch.describe_alarms()
            for alarm in alarms.get("MetricAlarms", []):
                logs.append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "type": "cloudwatch_alarm",
                    "data": alarm
                })
            
            logger.info("aws_logs_fetched", count=len(logs))
            return logs
        except Exception as e:
            logger.error("aws_fetch_failed", error=str(e))
            return []
    
    def parse_log(self, raw_log: dict) -> dict:
        log_type = raw_log.get("type", "unknown")
        data = raw_log.get("data", {})
        
        if log_type == "ec2_instance":
            instance_id = data.get("InstanceId", "unknown")
            state = data.get("State", {}).get("Name", "unknown")
            
            severity = "CRITICAL" if state == "terminated" else "WARNING" if state == "stopped" else "INFO"
            
            return {
                "source": "aws",
                "severity": severity,
                "service_name": f"AWS-EC2-{instance_id}",
                "message": f"EC2 instance {instance_id}: {state}",
                "error_code": "AWS_EC2_TERMINATED" if state == "terminated" else None,
                "raw_payload": json.dumps(data),
                "metadata": {
                    "instance_id": instance_id,
                    "instance_type": data.get("InstanceType"),
                    "state": state,
                    "availability_zone": data.get("Placement", {}).get("AvailabilityZone")
                }
            }
        
        elif log_type == "cloudwatch_alarm":
            alarm_name = data.get("AlarmName", "unknown")
            state = data.get("StateValue", "unknown")
            
            severity = "CRITICAL" if state == "ALARM" else "WARNING" if state == "INSUFFICIENT_DATA" else "INFO"
            
            return {
                "source": "aws",
                "severity": severity,
                "service_name": f"AWS-CloudWatch-{alarm_name}",
                "message": f"Alarm {alarm_name}: {state}",
                "error_code": "AWS_ALARM_TRIGGERED" if state == "ALARM" else None,
                "raw_payload": json.dumps(data),
                "metadata": {
                    "alarm_name": alarm_name,
                    "state": state,
                    "metric_name": data.get("MetricName")
                }
            }
        
        return {
            "source": "aws",
            "severity": "INFO",
            "service_name": "AWS",
            "message": "AWS status",
            "error_code": None,
            "raw_payload": json.dumps(data),
            "metadata": {}
        }
