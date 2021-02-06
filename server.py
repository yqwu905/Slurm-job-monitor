import json
import paramiko
from scp import SCPClient
import logging
import tool
import os
import socks
import socket
import job_control


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

    def download(self, remote, local, recursive=True):
        logging.info("Download {}@{}:{} to {}.".format(self.data['user'], self.data['server'], remote, local))
        self.scp.get(remote, local, recursive=recursive)
        logging.info("Download success.")

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
    def submit_job(self, remote, local):
        logging.debug("Start submit {} to {}@{}:{}".format(local, self.data['user'], self.data['server'], remote))
        folder = os.path.split(local)[-1]
        sFile = None
        for i in os.listdir(local):
            if os.path.isfile("{}/{}".format(local, i)):
                print(i)
                print(os.path.splitext(i)[-1])
                if os.path.splitext(i)[-1] == ".sbatch":
                    logging.debug("Find sbatch file {}".format(i))
                    sFile = i
                    break
        if sFile is None:
            logging.error("Error: No sbatch file found.")
            return True
        logging.debug("Start submit folder")
        self.upload(local, remote)
        logging.info("Upload Success.")
        logging.debug("Start submit sbatch")
        stdin, stdout, stderr = self.ssh.exec_command("sbatch {}/{}/{}".format(remote, folder, sFile))
        res, err = stdout.read().decode(), stderr.read().decode()
        if err != '':
            logging.error("Script submit error for {}@{}:{}".format(self.data['user'], self.data['server'], err))
            return False
        logging.info("script submit return: {}".format(res))
        print(res.split(" ")[-1])
        job_info = self.query_job(res.split(" ")[-1])
        job_list = job_control.jobs()
        job_list.add_job(job_info['JobId'], self.data['server'], self.data['user'], '{}/{}'.format(remote, folder),
                         local, job_info['JobState'])

    #
    def query_job(self, job_id):
        logging.debug("Query job info for {}@{}, job_id:{}.".format(self.data['user'], self.data['server'], job_id))
        stdin, stdout, stderr = self.ssh.exec_command("scontrol show job {}".format(job_id))
        res, err = stdout.read().decode(), stderr.read().decode()
        if err != '':
            logging.error("Job query error for {}@{}, job_id:{}, err:{}".format(self.data['user'], self.data['server'],
                                                                                job_id, err))
        logging.debug("Job query return:{}".format(res))
        logging.info("Job query success:{}".format(tool.analyze_scontrol_job(res)))
        return tool.analyze_scontrol_job(res)

    def update_job_status(self, job_id):
        logging.debug("Query job state for {}@{}, job_id:{}.".format(self.data['user'], self.data['server'], job_id))
        stdin, stdout, stderr = self.ssh.exec_command("sacct -j {} --format State".format(job_id))
        res, err = stdout.read().decode(), stderr.read().decode()
        if err != '':
            logging.error("Job update error for {}@{}, job_id:{}, err:{}".format(self.data['user'], self.data['server'],
                                                                                job_id, err))
        logging.debug("Job update return:{}".format(res))
        logging.info("Job update success:{}".format(tool.analyze_sacct_job(res)))
        return tool.analyze_sacct_job(res)

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
