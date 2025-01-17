import sys, os, csv, time, math, networkx as nx, shutil
sys.path.insert(0, os.getenv('lib'))
import utilv4 as util
realp=util.realp
#--------------------------------------------------------------------------------------------------
def initialize_master (cl_args, num_workers):   
    
    configs                        = load_simulation_configs (cl_args[1], 0) 
    
    M                              = load_network    (configs) 
    configs['number_of_genes']     = len(M.nodes())
    configs['sampling_rounds']     = min (configs['sampling_rounds_max'], (len(M.nodes())+len(M.edges()))*configs['sampling_rounds'])
    configs ['worker_load']        = int (math.ceil (float(configs['sampling_rounds']) / max(1,float(num_workers))))
    configs ['num_workers']        = num_workers
    
    save_network_stats         (M, configs)
    save_simulation_parameters (configs)  
    return M, configs
#--------------------------------------------------------------------------------------------------    
def initialize_worker(cl_args):
    configs = load_simulation_configs (cl_args[1], -1)
    return configs
#--------------------------------------------------------------------------------------------------    
def initialize_launcher(cl_args):
    configs = load_simulation_configs (cl_args[1], -1)
    return configs
#--------------------------------------------------------------------------------------------------
def load_simulation_configs (param_file, rank):
    param_file = realp(param_file)
    parameters = (open(param_file,'r')).readlines()
    assert len(parameters)>0
    configs = {}
    for param in parameters:
        param=param.strip()
        if len(param) > 0: #ignore empty lines
            if param[0] != '#': #ignore lines beginning with #
                param = param.split('=')
                if len (param) == 2:
                    key   = param[0].strip().replace (' ', '_')
                    value = param[1].strip()
                    configs[key] = value
    
    configs['network_file'] = realp(configs['network_file'])
    assert os.path.isfile(configs['network_file']) # the only mandatory parameters 
    configs['biased']              = configs['biased'] == 'True'
    bORu = 'u'
    if configs['biased']:
        bORu = 'b'
    configs['KP_solver_binary']    = realp(configs['KP_solver_binary'])
    configs['KP_solver_source']    = realp(configs['KP_solver_binary'])
    configs['KP_solver_name']      = configs['KP_solver_binary'].split('/')[-1].split('.')[0]  
    configs['stamp']               = configs['version']+configs['advice_upon'][0]+bORu+'_'+ configs['KP_solver_name']+'_'+configs['sampling_rounds']+'_'+ configs['BD_criteria']+'_'+configs['reduction_mode'] 
    configs['timestamp']           = time.strftime("%B-%d-%Y-h%Hm%Ms%S")
    configs['pressure']            = [float(p) for p in configs['pressure'].split(',') ]        
    configs['tolerance']           = [float(t) for t in configs['tolerance'].split(',') ]    
    configs['sampling_rounds_nX']  = configs['sampling_rounds']
    configs['sampling_rounds']     = int(''.join([d for d in configs['sampling_rounds'] if d.isdigit()]))
    configs['sampling_rounds_max'] = int (configs['sampling_rounds_max'])      
    configs['output_directory']    = util.slash (util.slash (realp(configs['output_directory'])) +configs['stamp'])
    configs['stats_dir']           = configs['output_directory']+"00_network_stats/" 
    configs['datapoints_dir']      = configs['output_directory']+"02_raw_instances_simulation/data_points/"
    configs['params_save_dir']     = configs['output_directory']+"02_raw_instances_simulation/parameters/"
    configs['progress_file']       = configs['output_directory']+"02_raw_instances_simulation/progress.dat"
    configs['progress_dir']        = configs['output_directory']+"02_raw_instances_simulation/"
    configs['DUMP_DIR']            = util.slash (configs['output_directory'])+"dump_raw_instances"
    configs['alpha']               = float(configs['alpha']) 
    #--------------------------------------------
    index = 1
    ALL_PT_pairs = {}
    for p in sorted (configs['pressure']):
        for t in sorted (configs['tolerance']):
            ALL_PT_pairs[index] = (p,t)
            index+=1
    completed_pairs                = []
    if os.path.isdir (configs['datapoints_dir']):
        for r,ds,fs in os.walk(configs['datapoints_dir']):
            RAW_FILES       = [f for f in fs if 'RAW' in f]            
            for raw_file in RAW_FILES:
                #file names must be as such: Vinayagam_RAW_INSTANCES_p020.0_t001.0_V3_MINKNAP_4X_BOTH_SCRAMBLE_June-13-2016-h09m15s55.csv
                split = raw_file.split('_')
                p     = float(''.join([d for d in split[-8] if d.isdigit() or d=='.']))
                t     = float(''.join([d for d in split[-7] if d.isdigit() or d=='.']))
                completed_pairs.append((p,t))
    configs['PT_pairs_dict'] = {}
    for index in sorted(ALL_PT_pairs.keys()):
        if not ALL_PT_pairs[index] in completed_pairs:
            configs['PT_pairs_dict'][index] = ALL_PT_pairs[index]        
    #--------------------------------------------   
    if rank == 0: #only master should create dir, prevents workers from fighting over creating the same dir
        while not os.path.isdir (configs['output_directory']):
            try:
                os.makedirs (configs['output_directory']) # will raise an error if invalid path, which is good
            except:
                time.sleep(5)
                print ("In load_simulation_configs(), rank=0, and Im still trying to create "+configs['output_directory']+" .. is this a correct path?")
                continue

    return configs
#--------------------------------------------------------------------------------------------------
def save_simulation_parameters (configs):
    params_directory = configs['params_save_dir']
    try:
        os.makedirs(params_directory) 
    except:
        pass #dir already exists, move on
    params_log = open (params_directory+configs['network_name']+"_params_"+configs['stamp'].upper()+"_"+configs['timestamp']+".txt",'w')
    
    for key in sorted(configs.keys()):    
        params_log.write(key.ljust(25,' ')+"= "+str(configs[key])+"\n")
#--------------------------------------------------------------------------------------------------
def save_network_stats (M, configs):
    stats_dir = configs['stats_dir'] 
    if os.path.isfile(stats_dir+configs ['network_name']+"_general_stats.txt"):
        return
    os.makedirs (stats_dir, exist_ok=True) #https://docs.python.org/3/library/os.html#os.makedirs
    
    if not configs['biased'] or configs['advice_upon'] == 'edges':
        degree_by_node = open (stats_dir+configs ['network_name']+"_node_degree.txt",'w')
        degree_by_node.write("Node\tdegree\tin_degree\tout_degree")
        for n in M.nodes():
            degree_by_node.write("\n"+n+"\t"+str(M.in_degree(n)+M.out_degree(n))+"\t"+str(M.in_degree(n))+"\t"+str(M.out_degree(n)))

    if configs['biased'] and configs['advice_upon']=='nodes':
        degree_by_node = open (stats_dir+configs ['network_name']+"_node_degree_with_conservation_scores.txt",'w')
        degree_by_node.write("Node\tdegree\tin_degree\tout_degree\tconservation_score")
        for n in M.nodes():
            degree_by_node.write("\n"+n+"\t"+str(M.in_degree(n)+M.out_degree(n))+"\t"+str(M.in_degree(n))+"\t"+str(M.out_degree(n))+"\t"+str(M.node[n]['conservation_score']))

    if configs['biased'] and configs['advice_upon']=='edges':
        edges_with_score = open (stats_dir+configs ['network_name']+"_edge_file_with_conservation_scores.txt",'w')
        edges_with_score.write("source\ttarget\tsign\tsource_degree\ttarget_degree\tconservation_score")        
        for e in M.edges():
            source, target, sign, deg_source, deg_target, score = e[0], e[1], M[e[0]][e[1]]['sign'], M.degree(e[0]), M.degree(e[1]), M[e[0]][e[1]]['conservation_score']
            edges_with_score.write("\n"+str(source)+'\t'+str(target)+'\t'+str(sign)+'\t'+str(deg_source)+'\t'+str(deg_target)+'\t'+str(score))

    two_way_edges = 0
    for n in M.nodes():
        for targeted_by_n in M[n].keys():
            if n in M[targeted_by_n].keys():
                two_way_edges +=1    
    
    general_stats  = open (stats_dir+configs ['network_name']+"_general_stats.txt",'w')
    general_stats.write ("Network name: "+configs['network_name']+"\nNetwork file: "+configs['network_file']+"\n"+str(M.number_of_nodes())+"\tnodes\n"+str(M.number_of_edges())+"\tedges\n"+str(len(nx.dominating_set(M)))+"\tdominating set\n"+str(two_way_edges/2)+"\tbi-directional edges")

#--------------------------------------------------------------------------------------------------    
def load_network (configs,undirected=False,quite=False): 
    file = realp(configs['network_file'])
    edges_file = open (file,'r') #note: with nx.Graph (undirected), there are 2951  edges, with nx.DiGraph (directed), there are 3272 edges
    M=nx.DiGraph()     
    duplicate_edges = []
    next(edges_file) #ignore the first line
    for e in edges_file: 
        interaction = [x.strip() for x in e.split()]
        assert len(interaction)>=2
        source, target = str(interaction[0]).upper(), str(interaction[1]).upper()
        
        # ignore duplicates interactions; duplicate is defined differently for directed/undirected
        if undirected: # (u,v) and (v,u) is the same in undirected
            if (source,target) in M.edges() or (target,source) in M.edges():
                duplicate_edges.append(source.ljust(25,' ')+target.ljust(25, ' '))
                continue 
        else:
            if (source,target) in M.edges():
                duplicate_edges.append(source.ljust(25,' ')+target.ljust(25, ' '))
                continue
        # if there's no sign, randomize it
        if (len(interaction) >2):
            if (str(interaction[2]) == '+'):
                Ijk=1
            elif  (str(interaction[2]) == '-'):
                Ijk=-1
            else:
                Ijk=util.flip()
                #print ("Error: bad interaction sign ("+str(interaction)+") in file "+configs['network_file']+"\nExiting...")
                #sys.exit()
        else:#randomize sign
            Ijk=util.flip()

        M.add_edge(source, target, sign=Ijk)    

    if len(duplicate_edges)>0 and not quite:
        print ("\nWARNING from init.py: found (and ignored) "+str(len(duplicate_edges))+ " duplicate edges, here is some of them: \n")
        for i in duplicate_edges[0:min(5,len(duplicate_edges))]:
            print (str(i))
    bi_directional = [ (u,v) for (u,v) in M.edges() if u in M[v].keys() and u!=v] 
    self_loops     = [ (u,v) for (u,v) in M.edges() if  u==v] 
    if len(bi_directional) > 0  and not quite:#how many bidirectional edges
        print("\nWARNING from init.py: found "+str(len(bi_directional))+" bidirectional edges, here is the first few:")
        print("\n".join([str(i) for i in bi_directional[0:min(len(bi_directional),5)]])+"\n")
    if len(self_loops) >0 and not quite:
        print("\nWARNING from init.py: found "+str(len(self_loops))+" self-loops, here is one of them: "+str(self_loops[0])+"\n")
    
    if undirected: #randomize direction
        for (u,v) in M.edges():
            if u==v:
                continue
            assert (v,u) not in M.edges() 
            if util.flip() == 1:
                s = M[u][v]['sign']
                M.remove_edge(u,v)
                M.add_edge(v,u,sign=s)
        bi_directional = [ (u,v) for (u,v) in M.edges() if u in M[v].keys() and u!=v] 
        if len(bi_directional) > 0  and not quite:#how many bidirectional edges
            print("\nWARNING from init.py: after randomization, there are "+str(len(bi_directional))+" bidirectional edges, here is the first few:")
            print("\n".join([str(i) for i in bi_directional[0:min(len(bi_directional),5)]])+"\n")

    # conservation scores:
    if not configs['biased']:
        return M
    else:
        return conservation_scores (M, configs)
#--------------------------------------------------------------------------------------------------
def conservation_scores (M, configs):
    degrees           = [d for d in M.degree().values()]
    set_degrees       = list(set(degrees))
    frequencies       = {d:degrees.count(d) for d in set_degrees}
    mind              = min(set_degrees)
    N                 = M.number_of_nodes() 
    meand             = float(sum(degrees))/float(N)
    a, b              = 0, 0.5
    alpha             = configs['alpha']
    if configs['advice_upon'] == 'edges':
        for e in M.edges():
            source_degree                    = M.degree (e[0])            
            #M[e[0]][e[1]]['conservation_score']  = 1.0/float(frequencies[source_degree])
            M[e[0]][e[1]]['conservation_score']  = scale(source_degree,  N, meand,  a, b, alpha)
    elif configs['advice_upon'] == 'nodes':
        for n in M.nodes():
            degree = M.degree(n)
            if degree > 0:
                #M.node[n]['conservation_score']  = 1.0/float(frequencies[degree]) 
                M.node[n]['conservation_score']  = scale(degree, N, meand,  a, b, alpha)
            else:
                M.node[n]['conservation_score']  = 0 #island node
    else:
        print ("FATAL: unrecognized value for configs['advice_upon'] parameter\nExiting ..")
        sys.exit(1)
    return M
#--------------------------------------------------------------------------------------------------
def scale (d, N,  meand, a, b, alpha):#https://en.wikipedia.org/wiki/Feature_scaling
    if d <= meand:
        return 0
    numerator   = (b-a)*math.pow((d-meand),2)
    denumenator = N*b
    return  math.pow((float(numerator)/float(denumenator)) +a, alpha)
#--------------------------------------------------------------------------------------------------
def scale_archived (x, mind,maxd,a,b,alpha):
	# http://stackoverflow.com/questions/5294955/how-to-scale-down-a-range-of-numbers-with-a-known-min-and-max-value
	# mapping data in interval [mind, maxd] into interval [a,b]
	#        (b-a)(x - min)
	# f(x) = --------------  + a			<<< raise all this to power alpha to dodge the linearity
    #          max - min
    if x < mind:
        return 0
    numerator   = math.pow((b-a)*(x-mind), 2)
    denumenator = maxd-mind
    return  math.pow((float(numerator)/float(denumenator)) +a,alpha) 
#--------------------------------------------------------------------------------------------------
