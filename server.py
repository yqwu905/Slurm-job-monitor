import json
import paramiko
from scp import SCPClient
import logging
import tool
import os
import socks
import socket
import time


# 此类实现了与服务器的连接,任务查询与提交,文件上传,脚本生成等等.
class server:
    def __init__(self, data, proxy=False, proxy_host='127.0.0.1', proxy_port=1080):
        self.data = data
        if proxy:
            socks.setdefaultproxy(socks.PROXY_TYPE_SOCKS5, proxy_host, proxy_port)
            socket.socket = socks.socksocket
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        logging.debug("Start to establish ssh connection to {}@{}".format(self.data['user'], self.data['server']))
        self.ssh.connect(hostname=self.data['server'], username=self.data['user'], password=self.data['passwd'])
        self.scp = SCPClient(self.ssh.get_transport(), socket_timeout=15.0)

    # 函数说明:
    # 参数:filpath:本地文件相对路径或绝对路径;remote_filepath:服务器端相对路径(相对于服务器列表中的default_dir);
    # 返回值:无
    def upload(self, filepath, remote_filepath):
        logging.info("upload {} to {}@{}:{}/{}".format(filepath, self.data['user'], self.data['server'],
                                                       self.data['default_dir'], remote_filepath))
        try:
            if os.path.isdir(filepath):
                logging.debug("{} is a folder, set recursive to True".format(filepath))
            self.scp.put(filepath, remote_path=remote_filepath, recursive=os.path.isdir(filepath))
        except FileNotFoundError:
            logging.error("System cannot found {}.".format(filepath))
            logging.info("System cannot found {}.".format(filepath))
        else:
            logging.info("Upload success!")

    def __repr__(self):
        return "{}@{}".format(self.data['user'], self.data['server'])

    # 函数说明:查询服务器上正在执行的任务
    # 参数:无
    # 返回值:一个描述任务的dict构成的列表,关于相应dict请查阅tool.analyze_squeue_jobs
    def query_jobs(self):
        logging.debug("Start query job for {}@{}".format(self.data['user'], self.data['server']))
        stdin, stdout, stderr = self.ssh.exec_command("squeue")
        res, err = stdout.read().decode(), stderr.read().decode()
        if err != '':
            logging.warning(
                "Error occurred in query_jobs of {}@{}: {}".format(self.data['user'], self.data['server'], err))
        res = res.split('\n')[1:-1]
        job_list = list()
        for i in res:
            job_list.append(tool.analyze_squeue_jobs(i))
        return job_list

    # 函数说明:提交VASP任务至服务器
    # 参数:folder:VASP脚本文件夹;working_dir:工作目录(相对于default_dir);script_path:sbatch脚本路径.
    # 返回值:提交状态(True/False),任务信息.
    def submit_vasp_job(self, folder, script_path, working_dir=''):
        # logging.debug("Submit VASP job to {}@{}".format(self.data['user'], self.data['server']))
        # self.upload(folder, self.data['default_dir'] + working_dir)
        # logging.info("{}@{} VASP folder submitted successfully".format(self.data['user'], self.data['server']))
        stdin, stdout, stderr = self.ssh.exec_command("sbatch {}".format(script_path))
        res, err = stdout.read().decode(), stderr.read().decode()
        if err != '':
            logging.error("Script submit error for {}@{}:{}".format(self.data['user'], self.data['server'], err))
        logging.info("script submit return: {}".format(res))
        
    # 
    def query_job(self, id):
        logging.debug("Query job info for {}@{}, id:{}.".format(self.data['user'], self.data['server'], id))
        stdin, stdout, stderr = self.ssh.exec_command("scontrol show job {}".format(id))
        res, err = stdout.read().decode(), stderr.read().decode()
        if err != '':
            logging.error("Job query error for {}@{}, id:{}, err:{}".format(self.data['user'], self.data['server'], id, 
                                                                            err))
        logging.debug("Job query return:{}".format(res))
        logging.info("Job query success:{}".format(tool.analyze_scontrol_job(res)))


def load_server_list(json_path='./server_list.json', proxy=False, proxy_host='127.0.0.1', proxy_port=1080):
    with open(json_path, 'r') as fp:
        data = json.load(fp)
    server_list = list()
    for i in data[:1]:
        server_list.append(server(i, proxy, proxy_host=proxy_host, proxy_port=proxy_port))
        # res = server_list[-1].query_jobs()
        # for i in res:
        #     print(i)
        print("{} connect success!".format(server_list[-1]))
    return server_list
