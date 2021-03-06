import numpy as np
import networkx as nx
from mesa import Model
from mesa.time import RandomActivation, SimultaneousActivation
from mesa.datacollection import DataCollector

import sys
sys.path.insert(0,'..')
from model_SEIRX import*


## data collection functions ##

def count_E_resident(model):
    E = np.asarray(
        [a.exposed for a in model.schedule.agents if a.type == 'resident']).sum()
    return E


def count_I_resident(model):
    I = np.asarray(
        [a.infectious for a in model.schedule.agents if a.type == 'resident']).sum()
    return I


def count_I_symptomatic_resident(model):
    I = np.asarray([a.infectious for a in model.schedule.agents if
        (a.type == 'resident'and a.symptomatic_course)]).sum()
    return I


def count_I_asymptomatic_resident(model):
    I = np.asarray([a.infectious for a in model.schedule.agents if
        (a.type == 'resident'and a.symptomatic_course == False)]).sum()
    return I


def count_R_resident(model):
    R = np.asarray(
        [a.recovered for a in model.schedule.agents if a.type == 'resident']).sum()
    return R


def count_X_resident(model):
    X = np.asarray(
        [a.quarantined for a in model.schedule.agents if a.type == 'resident']).sum()
    return X


def count_E_employee(model):
    E = np.asarray(
        [a.exposed for a in model.schedule.agents if a.type == 'employee']).sum()
    return E


def count_I_employee(model):
    I = np.asarray(
        [a.infectious for a in model.schedule.agents if a.type == 'employee']).sum()
    return I


def count_I_symptomatic_employee(model):
    I = np.asarray([a.infectious for a in model.schedule.agents if
        (a.type == 'employee'and a.symptomatic_course)]).sum()
    return I


def count_I_asymptomatic_employee(model):
    I = np.asarray([a.infectious for a in model.schedule.agents if
        (a.type == 'employee'and a.symptomatic_course == False)]).sum()
    return I


def count_R_employee(model):
    R = np.asarray(
        [a.recovered for a in model.schedule.agents if a.type == 'employee']).sum()
    return R


def count_X_employee(model):
    X = np.asarray(
        [a.quarantined for a in model.schedule.agents if a.type == 'employee']).sum()
    return X


def check_reactive_resident_screen(model):
    return model.screened_agents['reactive']['resident']


def check_follow_up_resident_screen(model):
    return model.screened_agents['follow_up']['resident']


def check_preventive_resident_screen(model):
    return model.screened_agents['preventive']['resident']


def check_reactive_employee_screen(model):
    return model.screened_agents['reactive']['employee']


def check_follow_up_employee_screen(model):
    return model.screened_agents['follow_up']['employee']


def check_preventive_employee_screen(model):
    return model.screened_agents['preventive']['employee']

data_collection_functions = \
    {
    'resident':
        {
        'E':count_E_resident,
        'I':count_I_resident,
        'I_asymptomatic':count_I_asymptomatic_resident,
        'I_symptomatic':count_I_symptomatic_resident,
        'R':count_R_resident,
        'X':count_X_resident
         },
    'employee':
        {
        'E':count_E_employee,
        'I':count_I_employee,
        'I_asymptomatic':count_I_asymptomatic_employee,
        'I_symptomatic':count_I_symptomatic_employee,
        'R':count_R_employee,
        'X':count_X_employee
         }
    }




class SEIRX_nursing_home(SEIRX):
        

    def __init__(self, G, verbosity=0, testing=True,
        exposure_duration=4, time_until_symptoms=6, infection_duration=11, 
        quarantine_duration=14, subclinical_modifier=1,
        infection_risk_contact_type_weights={
            'very_far': 0.1, 'far': 0.5, 'intermediate': 1, 'close': 3},
        K1_contact_types=['close'], diagnostic_test_type='one_day_PCR',
        preventive_screening_test_type='one_day_PCR',
        follow_up_testing_interval=None, liberating_testing=False,
        index_case='employee', 
        agent_types={'type1': {'screening_interval': None,
                              'index_probability': None,
                              'transmission_risk': 0.015,
                              'reception_risk': 0.015}},
        age_transmission_risk_discount = {'slope':None, 'intercept':1},
        age_symptom_discount = {'slope':None, 'intercept':0.6},
        seed=None):

        super().__init__(G, verbosity, testing,
            exposure_duration, time_until_symptoms, infection_duration,
            quarantine_duration, subclinical_modifier,
            infection_risk_contact_type_weights,
            K1_contact_types, diagnostic_test_type,
            preventive_screening_test_type,
            follow_up_testing_interval, liberating_testing,
            index_case, agent_types, age_transmission_risk_discount,
            age_symptom_discount, seed)




        
        # data collectors to save population counts and agent states every
        # time step
        model_reporters = {}
        for agent_type in self.agent_types:
            for state in ['E','I','I_asymptomatic','I_symptomatic','R','X']:
                model_reporters.update({'{}_{}'.format(state, agent_type):\
                    data_collection_functions[agent_type][state]})

        model_reporters.update(\
            {
            'screen_residents_reactive':check_reactive_resident_screen,
            'screen_residents_follow_up':check_follow_up_resident_screen,
            'screen_residents_preventive':check_preventive_resident_screen,
            'screen_employees_reactive':check_reactive_employee_screen,
            'screen_employees_follow_up':check_follow_up_employee_screen,
            'screen_employees_preventive':check_preventive_employee_screen,
            'N_diagnostic_tests':get_N_diagnostic_tests,
            'N_preventive_screening_tests':get_N_preventive_screening_tests,
            'undetected_infections':get_undetected_infections,
            'predetected_infections':get_predetected_infections,
            'pending_test_infections':get_pending_test_infections
            })

        agent_reporters =\
            {
            'infection_state':get_infection_state,
            'quarantine_state':get_quarantine_state
             }

        self.datacollector = DataCollector(
            model_reporters = model_reporters,
            agent_reporters = agent_reporters)
