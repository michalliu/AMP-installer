#!/usr/bin/python
#-*- coding: utf-8 -*-

import os,sys,urllib,re,_winreg,shutil,subprocess,zipfile

reload(sys)
sys.setdefaultencoding('gbk')
#打印
def printLine(message):
	sys.stdout.write(message+"\r")
	sys.stdout.flush()
#HTTP下载
def download(url,filename=None,text=None):
	if not filename:
		filename = url.split('/')[-1].split('#')[0].split('?')[0]
	if not text:
		text = u"正在下载 %s" % filename 
	def report( block_count,block_size,total_size ):
		printLine("%s\t%3.1f%%" % ( text.encode('GBK'),min(100,float( block_count * block_size ) / total_size * 100 ) ))
	urllib.urlretrieve(url,filename,reporthook=report)
	print u"下载完毕 %s" % filename
	return os.path.join(os.getcwd(),filename)
#在子目录中搜索文件
def searchFile(pattern):
	for root,dirs,files in os.walk(os.getcwd()):
		for file in files:
			if re.match(pattern,file):
				return os.path.join(root,file)
	return None
#搜索注册表
def searchReg(filter_obj,main_key,sub_key):
	parent_key = _winreg.OpenKey(main_key,sub_key)
	for i in range( _winreg.QueryInfoKey(parent_key)[0] ):
		child = _winreg.OpenKey(parent_key,_winreg.EnumKey(parent_key,i))
		temp = {}
		if _winreg.QueryInfoKey(child)[1] > 0 :
			for j in range(_winreg.QueryInfoKey(child)[1]):
				value_name,value_data,value_data_type = _winreg.EnumValue(child,j)
				temp[value_name] = value_data 
			try:
				for filter_key in filter_obj.keys():
					if not ( filter_key in temp.keys() and filter_obj[filter_key].match(temp[filter_key]) ):
						raise Exception("not match") 
				return temp
			except:
				pass
		_winreg.CloseKey(child)
	_winreg.CloseKey(parent_key)
	return None
#反安装
def uninstall(reg_obj,display_opt=""):
	product_code = re.compile("{.*}").search(reg_obj["UninstallString"]).group(0)
	print u"正在卸载 %s 请稍候..." % reg_obj["DisplayName"]
	uninstall_str = "MsiExec.exe /X%s %s" % (product_code,display_opt)
	try:
		ret_code = subprocess.call(uninstall_str)
		if ret_code == 0:
			print u"卸载成功完成."
		return ret_code
	except OSError,e:
		print u"卸载失败,%s" % e 
		return -1
#安装MSI
def install(file_path,text=None,display_opt=""):
	#TODO:MsiExec在windows7下不支持绝对路径,转换为相对路径
	file_path = file_path.replace(os.getcwd(),'').replace('\\','')
	if not text:
		text = file_path.split('\\')[-1]
	print u"正在安装 %s 请稍候..." % text
	install_str = "MsiExec.exe /I %s %s" % (file_path,display_opt)
	try:
		ret_code = subprocess.call(install_str)
		if ret_code == 0:
			print u"安装成功完成."
		return ret_code
	except OSError,e:
		print u"安装失败,%s" % e
		return -1
#解压缩
def unzip(file,dir,report=True):
	try:
		shutil.rmtree(dir)
	except:
		pass
	os.mkdir(dir,777)
	zipfileobj = zipfile.ZipFile(file)
	for name in zipfileobj.namelist():
		if name.endswith('/'):
			os.mkdir(os.path.join(dir,name))
		else:
			outfile = open(os.path.join(dir,name),'wb')
			outfile.write(zipfileobj.read(name))
			outfile.close()
#反注释
def uncomment(leadingchar,str):
	return str[len(leadingchar):]
#询问目录
def askDir(**kwargs):
	import Tkinter, tkFileDialog
	root = Tkinter.Tk()
	root.withdraw()
	return tkFileDialog.askdirectory(parent=root,**kwargs)
#添加环境变量
#http://code.activestate.com/recipes/416087-persistent-environment-variables-on-windows/
def addEnv(path):
	env_path = r'SYSTEM\CurrentControlSet\Control\Session Manager\Environment'
	env_reg = _winreg.ConnectRegistry(None, _winreg.HKEY_LOCAL_MACHINE)
	env_reg_key = _winreg.OpenKey(env_reg, env_path, 0, _winreg.KEY_ALL_ACCESS)
	env_path_value = _winreg.QueryValueEx(env_reg_key,"path".upper())	
	if( path.lower() not in env_path_value[0].lower().split(";") ):
		print u"添加环境变量%s" % path
		_winreg.SetValueEx(env_reg_key,"path".upper(),0,_winreg.REG_EXPAND_SZ,"%s%s%s;" % ("" if env_path_value[0].endswith(";") else ";",env_path_value[0],path))
	_winreg.CloseKey(env_reg)
	_winreg.CloseKey(env_reg_key)

def main():
	config = {
		"Apache":{
			"url":"http://labs.renren.com/apache-mirror//httpd/binaries/win32/httpd-2.2.17-win32-x86-openssl-0.9.8o.msi",
			"validator":re.compile("^httpd-(.)*\.msi$",re.I)
			},
		"PHP":{
			"url":"http://cn.php.net/distributions/php-5.2.14-Win32.zip",
			"validator":re.compile("^php-(.)*\.zip$",re.I)
			},
		"MySQL":{
			"url":"http://mysql.ntu.edu.tw/Downloads/MySQL-5.1/mysql-5.1.51-win32.msi",
			"validator":re.compile("^mysql-(.)*\.msi$",re.I)
			}
	   }
	installer_files = {}

	for installer in config.keys():
		print u"正在搜索%s安装文件..." % installer
		installer_file = searchFile(config[installer]["validator"])

		if installer_file:
			print u"已找到%s安装文件%s" % (installer,installer_file)
		else:
			print u"自动下载所需文件，请稍候..."
			installer_file = download(config[installer]["url"])

		installer_files[installer] = installer_file

	#检测是否已经安装Apache，如已安装，要求先卸载旧版本
	apache_old_reg = searchReg( {"DisplayName":re.compile(r"^Apache\s+HTTP\s+Server.*\d$"),"UninstallString":re.compile(r".*")}, _winreg.HKEY_LOCAL_MACHINE, "SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall")
	
	#安装Apache（要求卸载旧版本）
	if apache_old_reg:
		uninstall(apache_old_reg,"/passive")
	install(installer_files["Apache"])

	#读取Apache安装路径
	apache_new_reg = searchReg( {"ServerRoot":re.compile(r".*")}, _winreg.HKEY_LOCAL_MACHINE, "SOFTWARE\\Apache Software Foundation\\Apache")
	apache_base = apache_new_reg["ServerRoot"]
	#服务器套件安装目录
	server_base = "\\".join(apache_base.split('\\')[:-2])	
	#在Apache安装目录下安装PHP
	php_base = os.path.join(server_base,installer_files['PHP'].split('\\')[-1].split('.zip')[0])
	#安装PHP
	print u"正在安装PHP到%s"%php_base
	unzip(installer_files["PHP"],php_base)

	#配置Apache
	print u"正在配置Apache..."
	httpd_conf = os.path.join(apache_base,'conf','httpd.conf')
	#首次运行
	try:
		httpd_conf_dist = open(httpd_conf+"-dist")
		httpd_conf_dist.close()
	except:
		shutil.copyfile(httpd_conf,httpd_conf+"-dist")

	httpd_file = open(httpd_conf+"-dist")
	httpd_file_new = ""
	httpd_doc_root = ""
	for httpd_config_line in httpd_file.readlines():
		templine = httpd_config_line.strip()
		if not (templine.startswith('#') or len(templine) == 0):
			if templine.startswith("DocumentRoot"):
				httpd_doc_root = templine.split(" ")[-1][1:-1]
			httpd_file_new = httpd_file_new + templine + "\r\n"
	httpd_doc_root_new = askDir(initialdir=httpd_doc_root,title='请选择网页文件根目录')
	httpd_file_new = re.compile("^DocumentRoot \"(.)*\"",re.M).sub("DocumentRoot \"%s\"" % httpd_doc_root_new,httpd_file_new,count=1)
	httpd_file_new = re.compile("^<Directory \"(.)*\">",re.M).sub("<Directory \"%s\">" % httpd_doc_root_new,httpd_file_new,count=1)
	#TODO:根据Apache版本判断加载不同的PHP DLL
	php_module = os.path.join(php_base,"php5apache2_2.dll")	
	httpd_file_php_config = """
								LoadModule php5_module "%s"\r\n
								AddHandler application/x-httpd-php .php\r\n
								PHPIniDir "%s"\r\n
								<FilesMatch \\.php$>\r\n
									SetHandler application/x-httpd-php\r\n
								</FilesMatch>\r\n
							""" % (php_module.replace('\\','/'),php_base.replace('\\','/')+'/')	
	httpd_file_new += httpd_file_php_config.replace("\t","")
	#print u"添加字段%s\r\n" % httpd_file_php_config.replace('\t','').replace('\r\n','')
	httpd_file.close()
	httpd_file = open(httpd_conf,"wb")
	httpd_file.write(httpd_file_new)
	httpd_file.close()

	#配置PHP
	print u"正在配置PHP..."
	php_conf = os.path.join(php_base,'php.ini')
	php_conf_dist = os.path.join(php_base,'php.ini-recommended')
	php_conf_new = ""
	php_conf_comment_leading = ";"
	php_conf_uncomment_list = ("php_gd2.dll","php_mhash.dll","php_mysql.dll","php_mysqli.dll","php_sockets.dll","php_curl.dll")
	for php_conf_dist_line in open(php_conf_dist).readlines():
		templine = php_conf_dist_line.strip()
		#启用模块或配置
		if templine.startswith(";default_charset"):
			templine = "default_charset=\"utf-8\""
		if templine.split("=")[-1] in php_conf_uncomment_list:
			templine = uncomment(php_conf_comment_leading,templine)
		if not (templine.startswith(';') or len(templine) == 0):
			#PHP扩展模块路径
			if templine.startswith("short_open_tag"):
				templine = "short_open_tag = On"
			if templine.startswith("doc_root"):
				templine = "doc_root = \"%s\"" % httpd_doc_root_new.replace("/","\\")
			if templine.startswith('extension_dir'):
				templine = "extension_dir = \"%s\"" % os.path.join(php_base,'ext')
			php_conf_new = php_conf_new + templine + "\r\n"
	php_conf_file = open(php_conf,"wb")
	php_conf_file.write(php_conf_new)
	php_conf_file.close()
	#准备php zlib see php -i | find 'curl'
	if not searchFile(re.compile("^zlib.zip$",re.I)):
		download("http://nchc.dl.sourceforge.net/project/libpng/zlib/1.2.5/zlib125-dll.zip",filename="zlib.zip")
	unzip(os.path.join(os.getcwd(),"zlib.zip"),"zlib")
	shutil.copyfile(os.path.join(os.getcwd(),"zlib","zlib1.dll"),os.path.join(php_base,'zlib.dll'))
	#拷贝libmysql
	try:
		shutil.copyfile(os.path.join(php_base,'libmysql.dll'),os.path.join(apache_base,'bin\\libmysql.dll'))
		shutil.copyfile(os.path.join(php_base,'libmhash.dll'),os.path.join(apache_base,'bin\\libmhash.dll'))
	except IOError,e:
		#文件已存在或不需要拷贝dll文件
		pass
	#添加PHP.ini到环境变量中
	addEnv(php_base)

	#安装MySQL
	install(installer_files["MySQL"])

	#重启Apache使配置生效
	print u"正在重启Apache,以使新配置生效..."
	httpd_exeuteable = os.path.join(apache_base,'bin\httpd.exe')
	print u"正在停止Apache..."
	#httpd_restart = subprocess.call("%s -k restart" % httpd_exeuteable)
	#修改了系统环境变量,因此需要完全停止apache
	httpd_restart = subprocess.call("%s -k stop" % httpd_exeuteable)
	print u"正在启动Apache..."
	httpd_restart = subprocess.call("%s -k start" % httpd_exeuteable)

	#显示安装结果 
	result = """
			<center>
			<script>document.title="安装报告";</script>
			<div style="width:600px;overflow:hidden;margin:0px auto;border:1px solid black;">
				<div><h1 style="color:green;">您已成功安装Apache+PHP+Mysql套件</h1></div>
				<div style="font-size:12px;">
					<a href="http://www.hellohtml5.com" style="color:#0063dc;background:none;">反馈问题</a>
                    <a href="http://code.google.com/p/wamp-helper/" style="color:#0063dc;background:none;">项目主页</a>
				</div>
				<h1></h1>
				<!--<iframe src="http://www.hellohtml5.com" width=0 height=0 style="display:none;"></iframe>-->
			</div>
			<br>
			</center>
			<?
				phpinfo();
			?>
			"""
	result_filename = 'wamp.php'
	result_file = open(os.path.join(httpd_doc_root_new,result_filename),'wb')
	result_file.write(result)
	import webbrowser
	webbrowser.open("http://localhost/%s" % result_filename)

if __name__ == '__main__':
	main()
