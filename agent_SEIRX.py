from mesa import Agent


class agent_SEIRX(Agent):
    '''
    An agent with an infection status. NOTe: this agent is not
    functional on it's own, as it does not implement a step()
    function. Therefore, every agent class that inherits from this
    generic agent class needs to implement their own step() function
    '''

    def __init__(self, unique_id, unit, model,
        exposure_duration, time_until_symptoms, infection_duration,
        verbosity):
        super().__init__(unique_id, model)
        self.verbose = verbosity
        self.ID = unique_id
        self.unit = unit

        ## epidemiological parameters drawn from distributions
        # NOTE: all durations are inclusive, i.e. comparison are "<=" and ">="
        # number of days agents stay infectuous

        # days after transmission until agent becomes infectuous
        self.exposure_duration = exposure_duration
        # days after becoming infectuous until showing symptoms
        self.time_until_symptoms = time_until_symptoms
        # number of days agents stay infectuous
        self.infection_duration = infection_duration


        ## agent-group wide parameters that are stored in the model class
        self.index_probability = self.model.index_probabilities[self.type]
        self.symptom_probability = self.model.age_symptom_discount['intercept']
        self.transmission_risk = self.model.transmission_risks[self.type]
        self.reception_risk = self.model.reception_risks[self.type]
        self.mask = model.masks[self.type]


        # modulate transmission and reception risk based mask wearing
        self.transmission_risk = self.mask_adjust_transmission(\
            self.transmission_risk, self.mask)
        self.reception_risk = self.mask_adjust_reception(\
            self.reception_risk, self.mask)


        ## infection states
        self.exposed = False
        self.infectious = False
        self.symptomatic_course = False
        self.symptoms = False
        self.recovered = False
        self.tested = False
        self.pending_test = False
        self.known_positive = False
        self.quarantined = False

        # sample given for test
        self.sample = None

        # staging states
        self.contact_to_infected = False

        # counters
        self.days_since_exposure = 0
        self.days_quarantined = 0
        self.days_since_tested = 0
        self.transmissions = 0
        self.transmission_targets = {}




    def mask_adjust_transmission(self, risk, mask):
        if mask:
            risk *= 0.5
        return risk


    # generic helper functions that are inherited by other agent classes
    def mask_adjust_reception(self, risk, mask):
        if mask:
            risk *= 0.7
        return risk


    # generic helper functions that are inherited by other agent classes
    def get_contacts(self, agent_group):
        contacts = [a for a in self.model.schedule.agents if
            (a.type == agent_group and self.model.G.has_edge(self.ID, a.ID))]
        return contacts


    def introduce_external_infection(self):
        if (self.infectious == False) and (self.exposed == False) and\
           (self.recovered == False):
            index_transmission = self.random.random()
            if index_transmission <= self.index_probability:
                self.contact_to_infected = True
                if self.verbose > 0:
                    print('{} {} is index case'.format(
                        self.type, self.unique_id))


    def transmit_infection(self, contacts, transmission_risk, base_modifier):
        for c in contacts:
            if (c.exposed == False) and (c.infectious == False) and \
               (c.recovered == False) and (c.contact_to_infected == False):

                # modify the transmission risk based on the contact type
                modifier = base_modifier * \
                           self.model.G.get_edge_data(self.ID, c.ID)['weight']
                # modify the transmission risk based on the reception risk of 
                # the receiving agent
                modifier *= self.model.reception_risks[c.type]

                modified_transmission_risk = 1 - transmission_risk * modifier

                # draw random number for transmission
                transmission = self.random.random()

                #print(modified_transmission_risk)

                if transmission > modified_transmission_risk:
                    c.contact_to_infected = True
                    self.transmissions += 1

                    # track the state of the agent pertaining to testing at the
                    # moment of transmission to count how many transmissions
                    # occur in which states
                    if self.tested and self.pending_test and \
                        self.sample == 'positive':
                        self.model.pending_test_infections += 1

                    self.transmission_targets.update({c.ID:self.model.Nstep})

                    if self.verbose > 0:
                        print('transmission: {} {} -> {} {}'
                        .format(self.type, self.unique_id, c.type, c.unique_id))

    def act_on_test_result(self):
        '''
        Function that gets called by the infection dynamics model class if a
        test result for an agent is returned. The function sets agent states
        according to the result of the test (positive or negative). Adds agents
        with positive tests to the newly_positive_agents list that will be
        used to trace and quarantine close (K1) contacts of these agents. Resets
        the days_since_tested counter and the sample as well as the 
        pending_test flag
        '''

        # the type of the test used in the test for which the result is pending
        # is stored in the pending_test variable
        test_type = self.pending_test

        if self.sample == 'positive':

            # true positive
            if self.model.Testing.tests[test_type]['sensitivity'] >= self.model.random.random():
                self.model.newly_positive_agents.append(self)
                self.known_positive = True

                if self.model.verbosity > 1:
                    print('{} {} returned a positive test (true positive)'
                        .format(self.type, self.ID))

                if self.quarantined == False:
                    self.quarantined = True
                    if self.model.verbosity > 0:
                        print('quarantined {} {}'.format(self.type, self.ID))

            # false negative
            else:
                if self.model.verbosity > 1:
                    print('{} {} returned a negative test (false negative)'\
                        .format(self.type, self.ID))
                self.known_positive = False

                if self.model.Testing.liberating_testing:
                    self.quarantined = False
                    if self.model.verbosity > 0:
                        print('{} {} left quarantine prematurely'\
                        .format(self.type, self.ID))

            self.days_since_tested = 0
            self.pending_test = False
            self.sample = None

        elif self.sample == 'negative':

            # false positive
            if self.model.Testing.tests[test_type]['specificity'] <= self.model.random.random():
                self.model.newly_positive_agents.append(self)
                self.known_positive = True

                if self.model.verbosity > 1:
                    print('{} {} returned a positive test (false positive)'\
                        .format(self.type, self.ID))

                if self.quarantined == False:
                    self.quarantined = True
                    if self.model.verbosity > 0:
                        print('quarantined {} {}'.format(self.type, self.ID))

            # true negative
            else:
                if self.model.verbosity > 1:
                    print('{} {} returned a negative test (true negative)'\
                        .format(self.type, self.ID))
                self.known_positive = False

                if self.model.Testing.liberating_testing:
                    self.quarantined = False
                    if self.model.verbosity > 0:
                        print('{} {} left quarantine prematurely'\
                        .format(self.type, self.ID))

            self.days_since_tested = 0
            self.pending_test = False
            self.sample = None

    def become_exposed(self):
        if self.verbose > 0:
            print('{} exposed: {}'.format(self.type, self.unique_id))
        self.exposed = True
        self.contact_to_infected = False


    def become_infected(self):
        self.exposed = False
        self.infectious = True

        # determine if infected agent will show symptoms
        # NOTE: it is important to determine whether the course of the
        # infection is symptomatic already at this point, to allow
        # for a modification of transmissibility by symptomticity.
        # I.e. agents that will become symptomatic down the road might
        # already be more infectious before they show any symptoms than
        # agents that stay asymptomatic
        if self.random.random() <= self.symptom_probability:
            self.symptomatic_course = True
            if self.verbose > 0:
                print('{} infectious: {} (symptomatic course)'.format(self.type, self.unique_id))
        else:
            if self.verbose > 0:
                print('{} infectious: {} (asymptomatic course)'.format(self.type, self.unique_id))


    def show_symptoms(self):
        # determine if agent shows symptoms
        if self.symptomatic_course:
            self.symptoms = True
            if self.model.verbosity > 0:
                print('{} {} shows symptoms'.format(self.type, self.ID))


    def recover(self):
        self.infectious = False
        self.symptoms = False
        self.recovered = True
        self.days_since_exposure = 0
        if self.verbose > 0:
            print('{} recovered: {}'.format(self.type, self.unique_id))


    def leave_quarantine(self):
        if self.verbose > 0:
            print('{} released from quarantine: {}'.format(
                self.type, self.unique_id))
        self.quarantined = False
        self.days_quarantined = 0


    def advance(self):
        '''
        Advancing step: applies infections, checks counters and sets infection 
        states accordingly
        '''

        # determine if a transmission to the agent occurred
        if self.contact_to_infected == True:
            self.become_exposed()

        # determine if agent has transitioned from exposed to infected
        if self.days_since_exposure == self.exposure_duration:
            self.become_infected()

        if self.days_since_exposure == self.time_until_symptoms:
            self.show_symptoms()

        if self.days_since_exposure == self.infection_duration:
            self.recover()

        # determine if agent is released from quarantine
        if self.days_quarantined == self.model.quarantine_duration:
            self.leave_quarantine()

        # if there is a pending test result, increase the days the agent has
        # waited for the result by 1 (NOTE: results are collected by the 
        # infection dynamics model class according to days passed since the test)
        if self.pending_test:
            self.days_since_tested += 1

        if self.quarantined:
            self.days_quarantined += 1
            self.model.quarantine_counters[self.type] += 1

        if self.exposed or self.infectious:
            self.days_since_exposure += 1

        # reset tested flag at the end of the agent step
        self.tested = False
        
