#!/usr/bin/python
###############################################################################
#     ___                        ___         _      _                 _       #
#    / _ \ _ __  ___ __ _ __ _  | _ \___ _ _(_)_ __| |_  ___ _ _ __ _| |___   #
#   | (_) | '  \/ -_) _` / _` | |  _/ -_) '_| | '_ \ ' \/ -_) '_/ _` | (_-<   #
#    \___/|_|_|_\___\__, \__,_| |_| \___|_| |_| .__/_||_\___|_| \__,_|_/__/   #
#                  |___/                     |_|                              #
#                                                                             #
###############################################################################
# Name: check_ibm_spp.py
# Purpose: Monitor IBM Spectrum Protect Plus environment 
###############################################################################
# Changelog 0.0
# Initial test and debug
###############################################################################

import sys
import optparse
import json
import requests

#vars
spp_ipv4 = ''
spp_username = ''
spp_password = ''
spp_verify = False # Disable SSL.
# Status
ok = 0
warning = 1
critical = 2
unknown = 3

#Objects
class vSnap(object):
	def __init__(self,id,name,sizeTotal,sizeUsed,sizeFree):
		self.id = id
		self.name = name
		self.sizeTotal = sizeTotal
		self.sizeUsed = sizeUsed
		self.sizeFree = sizeFree

# ----------------------------------------------------------------------

def opt_args():
	parser = optparse.OptionParser()
	parser.set_conflict_handler("resolve")
	parser.add_option('--host', action="store", dest="host")
	parser.add_option('--user', action="store", dest="user")
	parser.add_option('--password', action="store", dest="password")
	parser.add_option('--option', action="store", dest="option")
	parser.add_option('--warning', action="store", dest="warn_val", default=75)
	parser.add_option('--critical', action="store", dest="crit_val", default=90)	
	options, args = parser.parse_args()
	return options

# ----------------------------------------------------------------------

def login():
	# Ignore warning for SSL not being used
	from requests.packages.urllib3.exceptions import InsecureRequestWarning
	requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
	_requests = requests.post('https://' + spp_ipv4 + '/api/endeavour/session',
	auth=(spp_username, spp_password),
	headers={
		'Accept': 'application/json',
		'Content-type': 'application/json'
	},
	params="", data="", verify=spp_verify)
	_response = json.loads(_requests.text) # Convert to JSON
	_session_id = _response['sessionid']
	return _session_id

# ----------------------------------------------------------------------

def vsnap_info(session,warn_val,crit_val):
	space_warning = warn_val
	space_critical = crit_val
	status = 0
	ok_str = "Normal storage usage on vSnaps:\n"
	warn_str = "Warning storage usage on vSnaps:\n"
	crit_str = "Critical storage usage on vSnaps:\n"
	perfdata = " | "
	header={
		'X-Endeavour-Sessionid':  session,
		'Accept': 'application/json',
		'Content-type': 'application/json'
	}
	from requests.packages.urllib3.exceptions import InsecureRequestWarning
        requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
	_requests = requests.get('https://' + spp_ipv4 + '/api/storage',
	headers=header, verify=spp_verify)
	_response = json.loads(_requests.text)
	object_json = _response['storages']
	vsnaps = [] 	
	for keys in object_json:
		name = keys['name'].split('.')
		vsnap = vSnap(keys['id'],name[0],keys['statistics']['sizeTotal'],keys['statistics']['sizeUsed'],keys['statistics']['sizeFree'])
		vsnaps.append(vsnap)
		if vsnap.sizeTotal > 0:
			usage_percent = round((float(vsnap.sizeUsed)/float(vsnap.sizeTotal))*100,2)
			if usage_percent < space_warning:
				ok_str += vsnap.name+' space consumed '+str(usage_percent)+'%\n'
			elif usage_percent > space_warning and usage_percent < space_critical:
				warn_str += vsnap.name+' space consumed '+str(usage_percent)+'%\n'
				if status < warning: 
					status = 1
			elif usage_percent > space_critical:
				crit_str += vsnap.name+' space consumed '+str(usage_percent)+'%\n'
				status = 2
 
	#perfdata 'label'=value[UOM];[warn];[crit];[min];[max]
	perfdata = " | "
	for vsnap in vsnaps:
		perf_warn = int(vsnap.sizeTotal*(float(space_warning)/100))
        	perf_crit = int(vsnap.sizeTotal*(float(space_critical)/100))
		perfdata +=" '"+vsnap.name+"'="+str(vsnap.sizeUsed)+"B;"+str(perf_warn)+";"+str(perf_crit)+";0;"+str(vsnap.sizeTotal)
		
	print(ok_str + '\n' + warn_str + '\n' + crit_str + perfdata)
	return status

# ----------------------------------------------------------------------

opt = opt_args()
spp_ipv4 = opt.host
spp_username = opt.user
spp_password = opt.password
session = login()

sys.exit(vsnap_info(session,opt.warn_val,opt.crit_val))
