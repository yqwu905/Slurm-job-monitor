import logging
import os
import json
import requests


# 函数说明:此函数用于格式化squeue得到的job信息
# 参数:待解析的字符串
# 返回值:dict对象,包含job的id,partition,name,account,status,time,nodes_num,nodelist(reason)
def analyze_squeue_jobs(s):
    reason = None
    if '(' in s:
        reason = s[s.index('(') + 1:s.index(')')]
        s = s[:s.index('(') - 1] + " reason"
    items = s.split(' ')
    while '' in items:
        items.remove('')
    assert len(items) == 8, "squeue返回值解析错误:{}".format(s)
    if reason is None:
        reason = items[7]
    return {"job_id": items[0],
            "partition": items[1],
            "name": items[2],
            "user": items[3],
            "st": items[4],
            "time": items[5],
            "nodes": items[6],
            "nodelist(reason)": reason
            }


#
def analyze_scontrol_job(s):
    s = s[:s.index('Power')]
    data = {}
    while '=' in s:
        key = s[:s.index('=')].replace('\n', '')
        value = s[s.index('=') + 1:s.index(' ')].replace('\n', '')
        data[key] = value
        s = s[s.index(' ') + 1:]
        while s[0] == ' ':
            s = s[1:]
            if len(s) == 0:
                break
    return data


def analyze_sacct_job(s):
    status = s.split('\n')
    print(status)
    while '' in status:
        status.remove('')
    return status[-1]


# 函数说明:生成VASP脚本
# 参数:filename:生成的脚本路径;job_name:任务名称;code:脚本中要执行的指令;partition:提交的分区;time_lim:时间限制;module:需要加载的
# module列表;N:node数;n:核数
# 返回值:无
def generate_VASP_script(filename, job_name, code, partition='compute', time_lim='1:59:59', module=None, N=1, n=40):
    with open(filename, 'w') as fp:
        fp.write("#!/bin/bash --login\n")
        fp.write("#SBATCH -J {}\n".format(job_name))
        fp.write("#SBATCH -N {}\n".format(N))
        fp.write("#SBATCH -n {}\n".format(n))
        fp.write("#SBATCH -p {}\n".format(partition))
        fp.write("#SBATCH -t {}\n".format(time_lim))
        fp.write("#SBATCH --exclusive\n\n")
        fp.write("module purge\n")
        for i in module:
            fp.write("module load {}\n".format(i))
        fp.write("\n")
        fp.write("echo -n \"start time     \" > time\n")
        fp.write("date >> time\n\n")
        fp.write("ulimit -s unlimited\n")
        fp.write("export OMP_NUM_THREADS=1\n")
        fp.write("export I_MPI_ADJUST_ALLTOALLV=2\n")
        fp.write("export SNPSLMD_LICENSE_FILE='27021@10.212.32.51'\n")
        fp.write("code=\"{}\"\n\n".format(code))
        fp.write("MYPATH=$SLURM_SUBMIT_DIR\n")
        fp.write("NNODES=$SLURM_NNODES\n")
        fp.write("NCPUS=$SLURM_NTASKS\n")
        fp.write("PPN=$SLURM_NTASKS_PER_NODE\n\n")
        fp.write("echo Running on host `hostname`\n")
        fp.write("echo Time is `date`\n")
        fp.write("echo Directory is `pwd`\n")
        fp.write("echo SLURM job ID is $SLURM_JOBID\n")
        fp.write("echo This jobs runs on the following machine: `echo $SLURM_JOB_NODELIST | uniq`\n")
        fp.write("echo Number of Processing Elements is $NCPUS\n")
        fp.write("echo Number of mpiprocs per node is $PPN\n")
        fp.write("echo VASP Start Time is `date` running NCPUs=$NCPUS PPN=$PPN\n")
        fp.write("start=\"$(date +%s)\"\n")
        fp.write("time mpirun $code\n")
        fp.write("stop=\"$(date +%s)\"\n")
        fp.write("finish=$(( $stop-$start ))\n")
        fp.write("echo VASP $SLURM_JOBID  Job-Time  $finish seconds\n\n")
        fp.write("echo -n \"end   time     \" >> time\n")
        fp.write("date >> time\n")


# 函数说明:将DOS格式的文件(CRLF)转为Unix格式(LF).
# 参数:filepath:需要转换的文件地址;
# 返回值:无
def dos2unix(filepath):
    dos = b'\r\n'
    unix = b'\n'
    if os.path.isfile(filepath):
        with open(filepath, 'rb') as open_file:
            content = open_file.read()
        content = content.replace(dos, unix)
        with open(filepath, 'wb') as open_file:
            open_file.write(content)
    if os.path.isdir(filepath):
        for dirpath, dirname, filenames in os.walk(filepath):
            for filename in filenames:
                logging.debug("Executing {}.".format(os.path.join(dirpath, filename)))
                dos2unix(os.path.join(dirpath, filename))


# 函数说明:初始化工作目录,检测server_list.json的存在,并创建job_list.json
# 参数:无
# 返回值:server_list.json存在则返回True,否则返回False
def init():
    if not os.path.exists('./server_list.json'):
        logging.error("server_list.json not exist!")
        logging.error("Init failed.")
        return False
    if not os.path.exists('job_list.json'):
        logging.debug("job_list.json not exist, creat by default.")
        data = []
        with open('./job_list.json', 'w') as fp:
            json.dump(data, fp)
    logging.info("Init success")
    return True


# 函数说明：检查是否有更新
# 参数:无
# 返回值:表示是否有更新的bool,以及更新描述字符串
def check_update():
    version = "v1.1.2"
    url = "https://api.github.com/repos/yqwu905/Slurm-job-monitor/releases/latest"
    r = requests.get(url)
    data = json.loads(r.text)
    if data['tag_name'] == version:
        return False, None
    else:
        return True, [f"<font color='red'>可更新的版本发现:{data['tag_name']}<font>",
                      f"<font color='red'>更新描述:{data['name']}<font>",
                      f"<font color='red'>更新特性:{data['body']}<font>"]
