import random, networkx as nx, math, os, sys, time
try:
    xrange
except NameError:
    xrange = range
#----------------------------------------------------------------------------  
def sample_p_genes(nodes,p):
    return  random.SystemRandom().sample(nodes,p) 
#--------------------------------------------------------------------------------------------------
def advice(list_p):
    a = {}
    for n in list_p: 
        a[n]=flip()
    return a
#--------------------------------------------------------------------------------------------------
def slash(path):
    return path+(path[-1] != '/')*'/'
#--------------------------------------------------------------------------------------------------
def flip():
    return random.SystemRandom().choice([1,-1])
#--------------------------------------------------------------------------------------------------    
def load_network (network_file):
    edges_file = open (network_file,'r') #note: with nx.Graph (undirected), there are 2951  edges, with nx.DiGraph (directed), there are 3272 edges
    M=nx.DiGraph()     
    next(edges_file) #ignore the first line
    for e in edges_file: 
        interaction = e.split()
        assert len(interaction)>=2
        source, target = str(interaction[0]), str(interaction[1])
        if (len(interaction) >2):
            if (str(interaction[2]) == '+'):
                Ijk=1
            elif  (str(interaction[2]) == '-'):
                Ijk=-1
            else:
                print ("Error: bad interaction sign in file "+network_file+"\nExiting...")
                sys.exit()
        else:
            Ijk=flip()     
        M.add_edge(source, target, sign=Ijk)    
    return M
#--------------------------------------------------------------------------------------------------    
def load_simulation_configs (param_file):

    parameters = (open(param_file,'r')).readlines()
    assert len (parameters) > 0
    network_name         =  parameters[0].split('=')[1].strip()
    network_file         =  parameters [1].split('=')[1].strip()    
    output_directory     =  slash (parameters[2].split('=')[1].strip()) 
    simulation_mode      =  parameters [3].split('=')[1].strip()
    sampling_threshold   =  int (parameters [4].split('=')[1].strip())
    pressure             =  [float (p) for p in parameters [5].split('=')[1].strip().split(',')]
    tolerance            =  [float (t) for t in  parameters [6].split('=')[1].strip().split(',')] 
    BD_criteria          =  parameters[7].split('=')[1].strip() 
   
    
    assert os.path.isdir(output_directory) and os.path.isfile(network_file)


    return [network_name, network_file, output_directory, simulation_mode, sampling_threshold, pressure, tolerance, BD_criteria]
#--------------------------------------------------------------------------------------------------
def getCommandLineArgs():
    if len(sys.argv) < 2:
        print ("Usage: python3 EbCS.py [/absolute/path/to/configs/file.txt]\nExiting..\n")
        sys.exit()
    return str(sys.argv[1])                    
#--------------------------------------------------------------------------------------------------
def instance_generator (M, Ps, sampling_threshold, BD_criteria_function, BD_criteria_name, network_name):
    output = os.path.join(os.getcwd(),network_name+'_instances_'+BD_criteria_name)
    if not os.path.isdir(output):
        os.mkdir(output)
    for p in Ps:   
        logger = open (slash(output)+"correlation_p"+str(p)+".csv","w")
        Bs=[]
        Ds=[]
        
        #calculate p% of nodes
        P_nodes = math.ceil ((float(p)/100.0)*len(M.nodes()))   

        print (str(sampling_threshold)+" instances at "+"p = "+str(p))
        for i in range (sampling_threshold):
            
            kp_instance = BD_criteria_function (M, advice(sample_p_genes(M.nodes(),P_nodes)), 0)
            for key in kp_instance[0].keys():
                Bs.append(kp_instance[0][key])
                Ds.append(kp_instance[1][key])
        
        if len(Bs) >0:
            for b in Bs:
                logger.write(str(b)+' ')
            logger.write('\n')
            for d in Ds:
                logger.write(str(d)+' ')
#--------------------------------------------------------------------------------------------------                
def BDT_calculator_source (M, Advice, T_percentage):
    BENEFITS, DAMAGES, relevant_edges = {}, {}, 0
    for target in Advice.keys():
        for source in M.predecessors (target):
            relevant_edges +=1
            if M[source][target]['sign']==Advice[target]:      #in agreement with the Oracle
                ######### REWARDING the source node ###########
                if source in BENEFITS.keys():
                    BENEFITS[source]+=1
                else:
                    BENEFITS[source]=1
                    if source not in DAMAGES.keys():
                        DAMAGES[source]=0    
            else:                                              #in disagreement with the Oracle
                ######### PENALIZING the source node ##########
                if source in DAMAGES.keys():
                    DAMAGES[source]+=1
                else:
                    DAMAGES[source]=1
                    if source not in BENEFITS.keys():
                        BENEFITS[source]=0
    
    T_edges = max (1, math.ceil (relevant_edges*(T_percentage/100)))
    
    assert len(BENEFITS.keys())==len(DAMAGES.keys())
    return [BENEFITS, DAMAGES, T_edges]
#--------------------------------------------------------------------------------------------------                
def BDT_calculator_target (M, Advice, T_percentage):
    BENEFITS, DAMAGES, relevant_edges = {}, {}, 0
    for target in Advice.keys():
        for source in M.predecessors (target):
            relevant_edges +=1
            if M[source][target]['sign']==Advice[target]:      #in agreement with the Oracle  
                ######### REWARDING the target node ###########
                if target in BENEFITS.keys():
                    BENEFITS[target]+=1
                else:
                    BENEFITS[target]=1
                    if target not in DAMAGES.keys():
                        DAMAGES[target]=0   
            else:                                              #in disagreement with the Oracle
                ######### PENALIZING the target node ##########
                if target in DAMAGES.keys():
                    DAMAGES[target]+=1
                else:
                    DAMAGES[target]=1
                    if target not in BENEFITS.keys():
                        BENEFITS[target]=0
                ###############################################
    
    T_edges = max (1, math.ceil (relevant_edges*(T_percentage/100)))
    
    assert len(BENEFITS.keys())==len(DAMAGES.keys())
    return [BENEFITS, DAMAGES, T_edges]
#--------------------------------------------------------------------------------------------------                
def BDT_calculator_both (M, Advice, T_percentage):
    BENEFITS, DAMAGES, relevant_edges = {}, {}, 0
    for target in Advice.keys():
        for source in M.predecessors (target):
            relevant_edges +=1
            if M[source][target]['sign']==Advice[target]:      #in agreement with the Oracle
                ######### REWARDING the source node ###########
                if source in BENEFITS.keys():
                    BENEFITS[source]+=1
                else:
                    BENEFITS[source]=1
                    if source not in DAMAGES.keys():
                        DAMAGES[source]=0    
                ######### REWARDING the target node ###########
                if target in BENEFITS.keys():
                    BENEFITS[target]+=1
                else:
                    BENEFITS[target]=1
                    if target not in DAMAGES.keys():
                        DAMAGES[target]=0   
                ###############################################
                ###############################################
            else:                                              #in disagreement with the Oracle
                ######### PENALIZING the source node ##########
                if source in DAMAGES.keys():
                    DAMAGES[source]+=1
                else:
                    DAMAGES[source]=1
                    if source not in BENEFITS.keys():
                        BENEFITS[source]=0
                ######### PENALIZING the target node ##########
                if target in DAMAGES.keys():
                    DAMAGES[target]+=1
                else:
                    DAMAGES[target]=1
                    if target not in BENEFITS.keys():
                        BENEFITS[target]=0
                ###############################################
    
    T_edges = max (1, math.ceil (relevant_edges*(T_percentage/100)))
    
    assert len(BENEFITS.keys())==len(DAMAGES.keys())
    return [BENEFITS, DAMAGES, T_edges]
#--------------------------------------------------------------------------------------------------

###################################################################################################                                    
#--------------------------------------------------------------------------------------------------
if __name__ == "__main__":   
    t0 = time.time() 


    configs                 = load_simulation_configs (getCommandLineArgs()) 
    network_name            = configs [0]
    network_file            = configs [1]
    output_directory        = configs [2]
    simulation_mode         = configs [3]
    sampling_threshold      = configs [4]
    pressure                = configs [5]
    tolerance               = configs [6]
    BD_criteria             = configs [7]
    

    BD_criteria_function = None
    if BD_criteria == 'source':
        BD_criteria_function = BDT_calculator_source
    elif BD_criteria == 'target':
        BD_criteria_function = BDT_calculator_target
    else:
        BD_criteria_function = BDT_calculator_both
    
    
    M                          = load_network    (network_file)    
    
    sampling_threshold         = min (sampling_threshold, (    len(M.nodes())+len(M.edges())   )*2)
    
    if (len(pressure) != 0):
        instance_generator (M, pressure, sampling_threshold, BD_criteria_function, BD_criteria, network_name)

    t1 = time.time() 
    print ("done: "+str(int(t1-t0)) +" seconds")
    
#--------------------------------------------------------------------------------------------------
###################################################################################################                                
#--------------------------------------------------------------------------------------------------
