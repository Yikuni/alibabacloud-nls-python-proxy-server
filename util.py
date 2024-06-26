# coding=utf-8
import os
import time
import json
from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.request import CommonRequest
from config import ALIYUN_AK_ID, ALIYUN_AK_SECRET
# 创建AcsClient实例
client = AcsClient(
   ALIYUN_AK_ID,
   ALIYUN_AK_SECRET,
   "cn-shanghai"
)

def genToken():
   # 创建request，并设置参数。
   request = CommonRequest()
   request.set_method('POST')
   request.set_domain('nls-meta.cn-shanghai.aliyuncs.com')
   request.set_version('2019-02-28')
   request.set_action_name('CreateToken')

   try:
      response = client.do_action_with_exception(request)

      jss = json.loads(response)
      if 'Token' in jss and 'Id' in jss['Token']:
         token = jss['Token']['Id']
         expireTime = jss['Token']['ExpireTime']
         return token
   except Exception as e:
      print(e)
      return None