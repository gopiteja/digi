"""
@Author : Akshat Goyal
"""
try:
	from app.da_bizRul_db_impl import BusinessRulesDAOImpl
except:
	from da_bizRul_db_impl import BusinessRulesDAOImpl

class DABizRulFactory:
	def get_dao_bizRul(impl='db'):
		if impl == 'db':
			return BusinessRulesDAOImpl()
		else:
			print("not implemented")
			return None
