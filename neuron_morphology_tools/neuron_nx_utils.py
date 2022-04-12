"""
Purpose: tools that will help process a neuron that
is represented as a networkx graph

"""
import networkx_utils as xu
import numpy as np
import pandas as pd
import system_utils as su

soma_node_name_global = "S0"
node_label = "u"

dynamic_attributes_default = (
 'spine_data',
 'synapse_data',
 'width_data',
  'skeleton_data')
import copy
def delete_attributes(
    G,
    inplace = True,
    attributes=None,
    verbose = False
    ):
    
    if not inplace:
        G = copy.deepcopy(G)
    
    if attributes is None:
        attributes = list(nxu.dynamic_attributes_default)
    
    return xu.delete_node_attributes(
        G,
        attributes=attributes,
        verbose = verbose)


def name_from_G(G,append=None):
    graph_attr = xu.graph_attr_dict(G)
    segment_id = graph_attr.get("segment_id",None)
    split_index = graph_attr.get("split_index",None)
    nucleus_id = graph_attr.get("nucleus_id",None)
    
    name = f"seg_{segment_id}_{split_index}_nucleus_{nucleus_id}"
    if append is not None:
        name += f"_{append}"
    return name
    
def save_G(
    G,
    filepath=None,
    filename_append = None,
    delete_dynamic_attributes = True,
    verbose = False
    ):
    
    """
    Purpose: To save the graph
    nxu.save_G(G_ax,filename_append="axon_high_fid")
    """
    
    if delete_dynamic_attributes:
        G = nxu.delete_attributes(
            G,
            inplace = False,
            verbose = False)
    if filepath is None:
        filepath = f"./{nxu.name_from_G(G,append=filename_append)}"
    
    return su.compressed_pickle(G,filepath)

def load_G(filepath):
    return su.decompress_pickle(filepath)
    

def skeletal_length_on_path(G,path):
    return np.sum([G.nodes[k]["skeletal_length"] for k in path])

def calculate_soma_distance_to_data_objs(
    G,
    verbose = False,
    data_to_update = ("synapse_data","spine_data","width_data"),                     
    ):
    """
    Purpose: To set the soma distance for all attributes

    Pseudocode: 
    Iterate through all of the nodes with L in name
    1) Find the path back to the soma
    2) Calculate the sum of skeletal length back to the soma
    for each attrbute
    3) Add skeletal length to the upstream dist to get the soma distance

    """
    for node in G.nodes():
        if "L" not in node:
            continue
        if verbose:
            print(f"--working on node {node}--")
        inbetween_node_path = xu.shortest_path(G,"S0",node)[1:-1]
        data_to_update = ("synapse_data","spine_data","width_data")

        soma_dist_on_path = nxu.skeletal_length_on_path(G,inbetween_node_path)

        if verbose:
            print(f"inbetween_node_path = {inbetween_node_path}")
            print(f"soma_dist_on_path = {soma_dist_on_path}")

        for dtype in data_to_update:
            for obj in G.nodes[node][dtype]:
                obj["soma_distance"] = obj["upstream_dist"] + soma_dist_on_path
                
                
def draw_tree(
    G,
    draw_type = "dot",#"twopi" (the circular), "circo" (makes square like)
    node_size=4000,
    font_size = 20,
    font_color = "white",
    figsize=(32,32),
    **kwargs):
    
    xu.draw_tree(
        G,
        draw_type = draw_type,#"twopi" (the circular), "circo" (makes square like)
        node_size=node_size,
        font_size = font_size,
        font_color = font_color,
        figsize=figsize,
        **kwargs)
    
    
skeletal_length_min_starter_branches_global = 700
def small_starter_branches(
    G,
    skeletal_length_min = None,
    soma_node_name = None,
    verbose = False,
    ):
    """
    Purpose: To identify starting nodes may want to remove

    Pseuodocde: 
    1) Look for those with small lengths
    2) Look for those that neighbor the soma
    """
    if skeletal_length_min is None:
        skeletal_length_min = skeletal_length_min_starter_branches_global

    if soma_node_name is None:
        soma_node_name= soma_node_name_global

    small_nodes = xu.nodes_from_node_query(G,f"(skeletal_length < {skeletal_length_min})")
    if verbose:
        print(f"small_nodes = {small_nodes}")
    small_soma_neighbors= []
    if len(small_nodes) > 0:
        soma_partners = xu.downstream_nodes(G,soma_node_name)
        if verbose:
            print(f"soma_partners= {soma_partners}")
        small_soma_neighbors = list(set(small_nodes).intersection(set(soma_partners)))
        
    if verbose:
        print(f"small_soma_neighbors= {small_soma_neighbors}")
        
    return small_soma_neighbors

import neuron_nx_utils as nxu
import copy

def remove_small_starter_branches(
    G,
    skeletal_length_min= None,
    inplace = False,
    verbose = True,
    **kwargs):
    """
    Purpose: To remove small starter branches from 
    the graph
    
    Ex: 
    nxu.remove_small_starter_branches(G,verbose = True)
    """

    if not inplace:
        G = copy.deepcopy(G)

    sm_st_branches = nxu.small_starter_branches(G,verbose = verbose,**kwargs)

    for s_b in sm_st_branches:
        if verbose:
            print(f"Removing {s_b}")
        xu.remove_edge_reattach_children_di(G,s_b,inplace = True)

    return G

import numpy as np
def soma_radius(
    G,
    stat = "mean",
    verbose = False
    ):
    """
    Purpose: To find the [stat] distance of the soma from the neighbors
    """
    soma_neighbors = xu.downstream_nodes(G,soma_node_name_global)
    s_center = G.nodes[soma_node_name_global]["mesh_center"]
    endpoints_dist = np.linalg.norm([G.nodes[k]["endpoint_upstream"] - s_center for k in soma_neighbors],axis = 1)
    stat_dist = getattr(np,stat)(endpoints_dist)
    if verbose:
        print(f"soma_neighbors = {soma_neighbors}")
        print(f"endpoints_dist = {endpoints_dist}")
        print(f"{stat} dist = {stat_dist}")
    return stat_dist
    
    
# --------------- For exporting graph as differnt file types -------------
import networkx as nx
def export_swc_dicts(
    G,
    use_skeletal_coordinates = True,
    soma_node_name = soma_node_name_global,
    default_skeleton_pt = "mesh_center",
    default_compartment = "dendrite",#"undefined",
    center_on_soma= True,
    coordinate_divisor = 1000,
    width_divisor = 1000,
    verbose = False,
    return_df = False,
    ):
    """
    Purpose: To convert a Graph Neuron Object
    into a SWC file dict objects by creating dictionaries of all of the points

    Pseudocode: 
    In a depth first search manner of searching
    For each node: 
        1) get the skeleton points
        2) Get the compartment
        3) Get the parent idx

    """

    index = 0

    compartment_index_map = dict(
        dendrite = 0,
        soma = 1,
        axon = 2,
        basal = 3,
        apical = 4,
        apical_tuft = 4,
        oblique = 4,
        apical_shaft = 4,
        custom = 5,
        undefined = 6,
        glia = 7
    )

    center_point = G.nodes[soma_node_name]["mesh_center"]

    node_order = nx.dfs_preorder_nodes(G,source = "S0")
    node_to_index_map = dict()
    swc_dicts = []
    for n in node_order:
        if verbose:
            print(f"\n---Working on {n}")
        node_to_index_map[n] = []

        if use_skeletal_coordinates and n != soma_node_name:
            skeleton_pts = G.nodes[n]["skeleton_data"][1:]
        else:
            skeleton_pts = np.array([G.nodes[n][default_skeleton_pt]])

        if n == soma_node_name:
            parent_idx = -1
            width_points = [nxu.soma_radius(G,verbose = False)]
        else:
            parent_name = xu.parent_node(G,n)
            parent_idx = node_to_index_map[parent_name][-1]
            if use_skeletal_coordinates:
                width_points = [k["width"] for k in G.nodes[n]["width_data"]]
            else:
                width_points = [G.nodes[n]["width_new"]["no_spine_median_mesh_center"]]

        curr_compartment  = G.nodes[n]["compartment"]
        if curr_compartment is None:
            curr_compartment = default_compartment

        if center_on_soma:
            skeleton_pts = skeleton_pts - center_point

        if verbose:
            print(f"skeleton_pts = {skeleton_pts}")
            print(f"parent_idx= {parent_idx}")
            print(f"curr_compartment= {curr_compartment}")

        for i,coord in enumerate(skeleton_pts):
            index += 1

            if i == 0:
                curr_parent_idx = parent_idx
            else:
                curr_parent_idx = index - 1

            curr_dict = {
                "n":index,
                "type":compartment_index_map[curr_compartment],
                "x": coord[0]/coordinate_divisor,
                "y":coord[1]/coordinate_divisor,
                "z":coord[2]/coordinate_divisor,
                "radius": width_points[i]/width_divisor,
                "parent":curr_parent_idx,
            }
            node_to_index_map[n].append(index)

            swc_dicts.append(curr_dict) 
    
    if return_df:
        pd.DataFrame.from_records(swc_dicts)
    return swc_dicts

def export_swc_df(G,**kwargs):
    return pd.DataFrame.from_records(export_swc_dicts(G,return_df=True,**kwargs))


import file_utils as fileu
def export_swc_file(
    G,
    filename=None,
    filename_append = None,
    directory="./",
    filepath = None,
    verbose = False,
    **kwargs):
    """
    Purpose: Create a SWC file from 
    graph object
    """
    
    swc_dicts= nxu.export_swc_dicts(G,verbose = False)
    if filename is None:
        filename = f"seg_{G.graph['segment_id']}_split_{G.graph['split_index']}_nucleus_{G.graph['nucleus_id']}"

    if filename_append is not None:
        filename = f"{filename}_{filename_append}"
        
    if filename[-4:] != ".swc":
        filename += ".swc"
        
    return fileu.file_from_dicts(
        swc_dicts,
        filename = filename,
        directory = directory,
        filepath = filepath,
        seperation_character=" ",
        verbose = verbose
    )

# -------------- computing morphology metrics using morphopy -----
import morphopy_utils as mpu

def swc_df(G,flip_z = True,**kwargs):
    swc = nxu.export_swc_df(G)
    swc_df = mpu.swc_rotated_resampled(swc,resample=False,flip_z = flip_z,**kwargs)
    return swc_df

def morphometrics(
    G=None,
    swc = None,
    **kwargs
    ):
    
    if swc is None:
        swc = nxu.swc_df(G)
    
    
    #swc_df = mpu.swc_rotated_resampled(swc,resample=False,flip_z = True)
        
    return mpu.morphometrics(swc=swc,**kwargs)


# ------------ for querying neuron graphs ----
def axon_dendrite_nodes(
    G,
    compartment="axon",
    return_node_df=False,):
    
    node_df = xu.node_df_from_node_query(G,query=f"axon_compartment=='{compartment}'")
    if return_node_df:
        return node_df
    else:
        return node_df[node_label].to_numpy()
    
def axon_nodes(
    G,
    return_node_df=False):
    
    return nxu.axon_dendrite_nodes(
    G,
    compartment="axon",
    return_node_df=return_node_df,)

def dendrite_nodes(
    G,
    return_node_df=False):
    
    return nxu.axon_dendrite_nodes(
    G,
    compartment="dendrite",
    return_node_df=return_node_df,)

import time
def plot(
    G,
    verbose = False,
    xlim = None,
    ylim=None,
    zlim = None,
    **kwargs):
    
    
    #st = time.time()
    swc_df = nxu.swc_df(G)
    ntree_obj = mpu.ntree_obj_from_swc(swc=swc_df)
    mpu.plot_ntree(
        ntree_obj,
        xlim = xlim,
        ylim=ylim,
        zlim = zlim,
        **kwargs)

# --------- mapping errors to nodes ----------
def limb_from_node_name(name):
    return int(name[1:name.find("_")])

def branch_from_node_name(name):
    return int(name[name.find("_")+1:])

def limb_branch_nodes(G):
    return [k for k in G.nodes() if "S" not in k]

def all_limb_idxs_in_G(G):
    return np.sort(np.unique([nxu.limb_from_node_name(k)
                     for k in limb_branch_nodes(G)]))

def all_limb_graphs(G):
    return [limb_graph(G,k) for k in 
           nxu.all_limb_idxs_in_G(G)]

def limb_graph(
    G,
    limb_idx,
    branches_idx = None,
    verbose = False,
    ):
    """
    Purpose: To return a graph of a certain limb
    
    Ex: nxu.limb_graph(G_ax,limb_idx = 3,verbose = True)
    """
    if type(limb_idx) == str:
        limb_idx = int(limb_idx[1:])
        
    if limb_idx == -1:
        if verbose:
            print(f"Returning whole graph")
        return G
    
    subgraph_nodes = [k for k in nxu.limb_branch_nodes(G)
                     if nxu.limb_from_node_name(k) == limb_idx]
    if verbose:
        print(f"subgraph_nodes after limb restriction: {subgraph_nodes}")
    
    if branches_idx is not None:
        subgraph_nodes = [k for k in subgraph_nodes
                         if nxu.branch_from_node_name(k) in branches_idx]
        
        if verbose:
            print(f"subgraph_nodes after branch restriction: {subgraph_nodes}")
        
    return G.subgraph(subgraph_nodes)


def node_match_by_dict(
    dict1,
    dict2,
    attributes = (
        "endpoint_upstream",
        #"endpoint_downstream",
        "skeleton_vector_upstream",
    ),
    verbose = False,
    ):
    """
    Purpose: To compare whether two
    nodes are the same or not
    
    Ex: 
    node_match_by_dict(
    G_ax.nodes["L0_0"],
    G_ax.nodes["L0_1"],
    verbose = True
    )
    """
    
    match_flag = True
    
    for a in attributes:
        val1 = dict1[a]
        val2 = dict2[a]
        
        if "array" in str(type(val1)):
            comp_result = np.array_equal(val1,val2)
        elif type(val1) == list:
            comp_result = np.all([k1==k2 for k1,k2 in zip(val1,val2)])
        else:
            comp_result  = val1==val2
            
        if comp_result == False:
            match_flag = False
            if verbose:
                print(f"Did not have equal {a}: {val1},{val2}")
            
    
    return match_flag


def node_map(
    G_source,
    G_target,
    verbose = False,
    ):
    """
    Purpose: To find the matches of all the nodes
    of one graph to another:

    Pseudocode: 
    For each node in the source graph
        Iterate through the target graph nodes
            Compare the certain properties, and if all match then assign as the correct mapping
            
            
    nxu.node_map(
        G_source = G_ax,
        G_target = G_proof,
        verbose = True
    )
    """
    source_to_target_map = dict()

    for n in nxu.limb_branch_nodes(G_source):

        limb_idx = nxu.limb_from_node_name(n)
        matching_nodes = []
        for nt in nxu.limb_branch_nodes(G_target):

            limb_idx_t = nxu.limb_from_node_name(nt)
            if limb_idx != limb_idx_t:
                continue

            match_result = nxu.node_match_by_dict(
                G_source.nodes[n],
                G_target.nodes[nt],
            )

            if match_result:
                matching_nodes.append(nt)

        if verbose:
            print(f"Node {n} --> {matching_nodes}")

        if len(matching_nodes) > 1:
            raise Exception("More than 1 match")

        if len(matching_nodes) == 0:
            source_to_target_map[n] = None
            continue

        match = matching_nodes[0]

        if nxu.limb_from_node_name(n) != nxu.limb_from_node_name(match):
            raise Exception("Not on same limb")

        source_to_target_map[n] = match

    #check to see if unique
    final_matches = list([k for k in source_to_target_map.values()
                          if k is not None])
    if len(final_matches) != len(np.unique(final_matches)):
        raise Exception("Some repeats")
            
    return source_to_target_map
            
def nodes_without_match(
    G_source,
    G_target,
    verbose = False):
    
    curr_map = nxu.node_map(
        G_source,
        G_target)
    
    no_map = np.array([k for k,v in curr_map.items() if v is None])
    
    if verbose:
        print(f"Nodes with no match = {len(no_map)}")
        
    return no_map

import numpy_utils as nu
def skeleton_coordinates_from_G(
    G,
    include_upstream_node = False,
    verbose = False,
    return_node_names = False,
    ):
    """
    Purpose: To output the skeleton points of a graph
    and the node names those skeleton points came from
    
    Ex: 
    sk_pts,sk_names = nxu.skeleton_coordinates_from_G(
        G_ax,
    return_node_names=True,
    verbose = True)
    """

    total_skeleton_points = []
    total_node_names = []

    for n in nxu.limb_branch_nodes(G):
        skeleton_points = G.nodes[n]["skeleton_data"]
        if not include_upstream_node:
            upstream_coordinate = G.nodes[n]["endpoint_upstream"].reshape(-1,3)
            skeleton_points = nu.setdiff2d(skeleton_points,upstream_coordinate)

        node_names = np.array([n]*len(skeleton_points))

        if verbose:
            print(f"Node {n} has {len(skeleton_points)} skeleton points")

        total_skeleton_points.append(skeleton_points)
        total_node_names.append(node_names)

    if len(total_skeleton_points) > 0:
        total_skeleton_points = np.vstack(total_skeleton_points)
        total_node_names = np.concatenate(total_node_names)
    else:
        total_skeleton_points = np.array([])
        total_node_names = np.array([])

    if verbose:
        print(f"Total skeleton points = {len(total_skeleton_points)}")

    if return_node_names:
        return total_skeleton_points,total_node_names
    else:
        return total_skeleton_points
    
    
from pykdtree.kdtree import KDTree
import pandas as pd

def split_location_node_map_df(
    G,
    split_locations,
    G_target = None,
    nodelist = None,
    distance_max = 5000,
    error_if_no_one_match = True,
    error_on_non_unique_node_names = True,
    verbose = False,
    verbose_loop = False,
    ):
    """
    Purpose: Want to map split locaitons to the nodes that
    were cut off due to proofreading with what rule was used to cut off

    Things can leverage:
        The limb name
        Nodes that shouldn't be mapped

    Pseudocode: 
    Iterate through all filters and limbs to work
    with the split locations and possible nodes to match with



    """

    split_info = []

    if G_target is not None and nodelist is None:
        nodelist = nxu.nodes_without_match(
            G_source = G,
            G_target=G_target,
            verbose = verbose )

    if nodelist is not None: 
        G_search = G.subgraph(nodelist)
    else:
        G_search = G

    split_counter = 0
    for filter_name,filter_splits in split_locations.items():
        if type(filter_splits) != dict:
            filter_splits = {"L-1":filter_splits}

        for limb_name,split_loc in filter_splits.items():
            G_limb = nxu.limb_graph(G_search,limb_name)

            sk_pts,sk_names = nxu.skeleton_coordinates_from_G(
                G_limb,
                return_node_names=True,
                verbose = False)

            if len(G_limb) == 0:
                raise Exception("Empty graph")

            for i,s in enumerate(split_loc):

                local_split = dict(limb_split_idx = i,
                                   limb_name = limb_name,
                                   coord = s,
                                  filter_name = filter_name)
                dist_from_split = np.linalg.norm(sk_pts - s,axis = 1)
                min_dist = np.min(dist_from_split)

                min_arg = np.where(dist_from_split == min_dist)[0]
                min_nodes = sk_names[min_arg]

                if len(min_nodes) != 1 and error_if_no_one_match:
                    raise Exception(f"Split {i} ({s}) had min_dist ({min_dist}) had more than one match ({min_nodes})")

                if error_if_no_one_match:
                    min_nodes = min_nodes[0]

                if min_dist > distance_max:
                    raise Exception(f"Split {i} ({s}) had min_dist ({min_dist}) that was greater than distance_max ({distance_max})")

                local_split["node"] = min_nodes
                local_split["min_distance"] =  min_dist

                split_info.append(local_split)
                split_counter += 1

                if verbose_loop:
                    print(f"local_split = {local_split}")

    split_df = pd.DataFrame.from_records(split_info)
    
    if error_on_non_unique_node_names:
        pass
    
    if verbose:
        print(f"Total split mappings: {len(split_df)}")
    
    return split_df


    
import neuron_nx_utils as nxu