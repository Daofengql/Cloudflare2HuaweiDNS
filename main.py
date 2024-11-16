# coding: utf-8

import os
import pandas as pd
import yaml
from loguru import logger
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkdns.v2.region.dns_region import DnsRegion
from huaweicloudsdkcore.exceptions import exceptions
from huaweicloudsdkdns.v2 import *

# 配置日志输出格式
logger.add("dns_management.log", format="{time} {level} {message}", level="INFO", rotation="1 MB", retention="7 days")


def load_config(file_path):
    """加载 YAML 配置文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            config = yaml.safe_load(file)
            logger.info("Configuration loaded successfully.")
            return config
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        raise


def initialize_dns_client(access_key, secret_key, region):
    """初始化 DNS 客户端"""
    credentials = BasicCredentials(ak=access_key, sk=secret_key)
    client = DnsClient.new_builder() \
        .with_credentials(credentials) \
        .with_region(DnsRegion.value_of(region)) \
        .build()
    logger.info("DNS client initialized.")
    return client


def extract_ip_list(file_path, n):
    """从 CSV 文件中提取前 n 个 IP 地址"""
    try:
        data = pd.read_csv(file_path, encoding='utf-8', nrows=n)
        ip_list = data.iloc[:, 0].tolist()
        logger.info(f"Extracted {len(ip_list)} IPs from {file_path}.")
        return ip_list
    except Exception as e:
        logger.error(f"Failed to extract IPs from CSV: {e}")
        raise


def get_zone_id(client, domain_name):
    """获取指定域名的 Zone ID"""
    try:
        request = ListPublicZonesRequest()
        request.name = domain_name
        response = client.list_public_zones(request)
        if response.zones:
            zone_id = response.zones[0].id
            logger.info(f"Zone ID for domain '{domain_name}': {zone_id}")
            return zone_id
        else:
            logger.warning(f"No Zone ID found for domain '{domain_name}'.")
            return None
    except exceptions.ClientRequestException as e:
        logger.error(f"Error while fetching Zone ID: {e.error_msg}")
        return None


def get_duplicate_records(client, zone_id, target_name, target_line, record_type):
    """获取相同 Name、Line 和 Type 的重复记录"""
    try:
        request = ShowRecordSetByZoneRequest()
        request.zone_id = zone_id
        response = client.show_record_set_by_zone(request)
        
        # 筛选相同 Name、Line 和 Type 的记录
        duplicates = [
            record for record in response.recordsets
            if record.name == target_name 
               and getattr(record, 'line', 'default') == target_line
               and record.type == record_type  # 根据记录类型筛选
        ]
        logger.info(f"Found {len(duplicates)} records with name '{target_name}', line '{target_line}' and type '{record_type}'.")
        return duplicates
    except exceptions.ClientRequestException as e:
        logger.error(f"Error while fetching duplicate records: {e.error_msg}")
        return []


def delete_duplicate_records(client, zone_id, records):
    """删除重复记录，保留第一个"""
    try:
        record_ids_to_delete = [record.id for record in records[1:]]  # 保留第一个记录
        if not record_ids_to_delete:
            logger.info("No duplicate records to delete.")
            return
        
        for record_id in record_ids_to_delete:
            request = DeleteRecordSetsRequest()
            request.zone_id = zone_id
            request.recordset_id = record_id
            client.delete_record_sets(request)
            logger.info(f"Deleted record ID: {record_id}")
    except exceptions.ClientRequestException as e:
        logger.error(f"Error while deleting duplicate records: {e.error_msg}")


def update_dns_record(client, zone_id, record_id, new_ips):
    """更新 DNS 记录，同时保持 TTL 和 Line 不变"""
    from huaweicloudsdkdns.v2 import BatchUpdateRecordSetWithLineReq, BatchUpdateRecordSet
    
    try:
        recordsets = [
            BatchUpdateRecordSet(
                id=record_id,
                records=new_ips  # 更新的记录内容
            )
        ]
        
        request = BatchUpdateRecordSetWithLineRequest()
        request.zone_id = zone_id
        request.body = BatchUpdateRecordSetWithLineReq(
            recordsets=recordsets  # 包含的记录集
        )

        client.batch_update_record_set_with_line(request)
        
        # 提取更新后的内容进行日志记录
        updated_records = new_ips
        logger.info(f"DNS Record updated successfully:")
        logger.info(f"Zone ID: {zone_id}")
        logger.info(f"Updated Record ID: {record_id}")
        logger.info(f"Updated Records: {updated_records}")
    except exceptions.ClientRequestException as e:
        logger.error(f"Error while updating DNS record: {e.status_code}, {e.error_msg}")


def create_dns_record(client, zone_id, target_name, target_line, new_ips, record_type="A"):
    """创建新的 DNS 记录"""
    try:
        request = CreateRecordSetWithLineRequest()
        request.zone_id = zone_id
        request.body = CreateRecordSetWithLineRequestBody(
            name=target_name,
            type=record_type,  # 使用配置中的记录类型
            records=new_ips,
            line=target_line,
            ttl=300  # 设置默认 TTL 值
        )

        response = client.create_record_set_with_line(request)
        logger.info(f"DNS Record created successfully:")
        logger.info(f"Zone ID: {zone_id}")
        logger.info(f"Record Name: {target_name}")
        logger.info(f"Record Line: {target_line}")
        logger.info(f"Record Type: {record_type}")  # 记录类型
        logger.info(f"Record IPs: {new_ips}")
        logger.info(f"Response: {response}")
    except exceptions.ClientRequestException as e:
        logger.error(f"Error while creating DNS record: {e.status_code}, {e.error_msg}")


def process_domain(dns_client, domain_config, csv_rows):
    """处理单个域名"""
    domain_name = domain_config["domain_name"]
    target_name = domain_config["target_name"]
    line = domain_config["line"]
    record_type = domain_config.get("type", "A")  # 默认类型为 A
    csv_file = domain_config["csv_file"]

    # 获取 Zone ID
    zone_id = get_zone_id(dns_client, domain_name)
    if not zone_id:
        logger.error(f"Failed to process domain '{domain_name}': Zone ID not found.")
        return

    # 获取重复记录
    duplicate_records = get_duplicate_records(dns_client, zone_id, target_name, line, record_type)

    # 如果记录不存在，则创建新记录
    if not duplicate_records:
        logger.info(f"No existing record found for name '{target_name}', line '{line}' and type '{record_type}' in domain '{domain_name}'. Creating new record...")
        new_ips = extract_ip_list(csv_file, csv_rows)
        create_dns_record(dns_client, zone_id, target_name, line, new_ips, record_type)
        return

    # 删除多余记录
    if len(duplicate_records) > 1:
        delete_duplicate_records(dns_client, zone_id, duplicate_records)

    # 提取新的 IP 列表
    new_ips = extract_ip_list(csv_file, csv_rows)

    # 更新剩余的第一个记录
    update_dns_record(dns_client, zone_id, duplicate_records[0].id, new_ips)


def main():
    try:
        # 加载配置
        config = load_config("config.yaml")
        huawei_cloud = config["huawei_cloud"]
        csv_rows = config["csv"]["n_rows"]
        domains = huawei_cloud["domains"]

        # 初始化 DNS 客户端
        dns_client = initialize_dns_client(
            huawei_cloud["access_key_id"],
            huawei_cloud["access_key_secret"],
            huawei_cloud["region"]
        )

        # 遍历每个域名
        for domain_config in domains:
            logger.info(f"Processing domain: {domain_config['domain_name']}, Record Type: {domain_config.get('type', 'A')}")
            process_domain(dns_client, domain_config, csv_rows)

    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    main()
