# ----------- For outputing for use in GNN
import system_utils as su
import neuron_nx_feature_processing as nxf
import neuron_nx_utils as nxu
import networkx as nx
import networkx_utils as xu
from pathlib import Path
import numpy as np
import time
def export_GNN_info_dict(
    G,
    features_to_output,
    axon_dendrite = None,
    remove_starter_branches = True,
    distance_threshold = 100_000,
    distance_threshold_min = None,
    divide_into_limbs = True,
    

    label_name = None,#"axon_label",
    graph_label = None,

    feature_matrix_dtype = "float",
    
    #output file features
    folder = "./",
    filename = None,
    description = None,
    verbose = False,
    
    return_filepaths = False,
    return_G_before_output = False,
    
    
    ):
    """
    To process a neuron object before output
    in dictionary format to be used by a GNN
    """
    print(f"return_filepaths =- {return_filepaths}")
    
    
    st = time.time()
    if label_name is None:
        if verbose:
            print(f"*** Warning label_name is None")
            
    if graph_label is None:
        if verbose:
            print(f"*** Warning graph_label is None")
    
    
    G_dict = xu.graph_attr_dict(G)
    
    if verbose:
        print(f"G_dict = {G_dict}")
    
    filename = nxu.name_from_G(G)
    
    if description is not None:
        filename += f"_{description}"
        
        
        
    filepaths = []

    # ----------- Does a lot of the preprocessing before outputting----------
    if axon_dendrite is not None:
        if verbose:
            print(f"Filtering for {axon_dendrite}")
        G = nxu.axon_dendrite_subgraph(
            G,
            compartment=axon_dendrite,
            include_soma = True,
            verbose = verbose,
            )
        
        
    if remove_starter_branches:
        G_filt = nxu.remove_small_starter_branches(
            G,
            verbose = verbose,
            maintain_skeleton_connectivity = True)
    else:
        G_filt = G
        

    if distance_threshold is not None:
        G_dist_filt = nxu.nodes_within_distance_upstream_from_soma(
            G_filt,
            verbose = verbose,
            distance_threshold = distance_threshold,
            return_subgraph = True,
        )
    else:
        G_dist_filt = G_filt
        
    if distance_threshold_min is not None:
        G_dist_filt = nxu.nodes_farther_than_distance_from_soma(
            G_dist_filt,
            verbose = verbose,
            distance_threshold = distance_threshold_min,
            return_subgraph = True,
            distance_type = "downstream",
        )
        

    if len(nxu.limb_branch_subgraph(G_dist_filt).nodes()) > 0:
        G_with_feats = nxf.filter_G_features(
                    G_dist_filt,
                    features=features_to_output,
                    inplace = False,
                    verbose = verbose,
                )
    else:
        G_with_feats = G_dist_filt
    
    if return_G_before_output:
        if divide_into_limbs:
            G_with_feats = nxu.limb_graphs_from_soma_connected_nodes(G_with_feats)
        return G_with_feats
    # ----------- Dividing up and outputting the files -----------
    if divide_into_limbs:
#         print(f"G_with_feats.nodes() = {G_with_feats.nodes()}")
#         import matplotlib.pyplot as plt
#         import networkx as nx
#         nx.draw(G_with_feats,with_labels = True)
#         plt.show()
        limb_graphs_for_axon = nxu.limb_graphs_from_soma_connected_nodes(G_with_feats)
        #print(f"len(limb_graphs_for_axon) = {len(limb_graphs_for_axon)}")
        for j,G_limb in enumerate(limb_graphs_for_axon):
            if verbose:
                print(f"Outputing limb {j}---")


            most_starting_branch = xu.most_upstream_node(G_limb)
            #converting to non-directional
            G_limb = nx.Graph(G_limb)

            G_limb = nxu.limb_branch_subgraph(G_limb)
            limb_info = xu.adjacency_feature_info(
                G = G_limb,
                return_df_for_feature_matrix = False,
                feature_matrix_dtype = feature_matrix_dtype,
                dense_adjacency=True

            )

            limb_info["label_name"] = label_name
            limb_info["graph_label"] = graph_label

            curr_filename = f"{filename}_limb_{j}_starting_branch_{most_starting_branch}"

            output_path = str((Path(folder)/Path(curr_filename)).absolute())

            if return_filepaths:
                ret_filepath = su.compressed_pickle(
                    limb_info,
                    output_path,
                    return_filepath=True,
                    verbose = verbose)
            else:
                ret_filepath = limb_info

            filepaths.append(ret_filepath)
    else:
        """
        Pseudocode: 
        1) Remove the soma from the graph
        2) Attach the label of the graph
        """
        if verbose:
            print()

        G_no_soma = nxu.soma_filter_by_complete_graph(G_with_feats,plot=False)
        G_no_soma = nx.Graph(G_no_soma)

        if len(G_no_soma.nodes()) > 0:
            G_info = xu.adjacency_feature_info(
                    G = G_no_soma,
                    return_df_for_feature_matrix = False,
                    feature_matrix_dtype = "float",
                    dense_adjacency=True

                )

            G_info["label_name"] = label_name
            G_info["graph_label"] = graph_label

            curr_filename = f"{filename}"
            output_path = str((Path(folder)/Path(curr_filename)).absolute())

            if return_filepaths:
                ret_filepath = su.compressed_pickle(
                        G_info,
                        output_path,
                        return_filepath=True,
                        verbose = verbose)
            else:
                ret_filepath = G_info

            filepaths.append(ret_filepath)

    if verbose:
        print(f"\n\n---Total time = {time.time() - st}")
        
        
    return filepaths
    
    

import system_utils as su
import networkx_utils as xu
import pandas as pd

import pandas as pd
import numpy_utils as nu
import pandas_utils as pu
def feature_df_from_gnn_info(
    gnn_info,
    return_data_labels_split = True,
    inf_fill_value = 10000,
    add_negative_label = False,
    label_name = None):
    
    
    df = pd.DataFrame(gnn_info["feature_matrix"])
    df.columns = gnn_info["features"]

    df=df.replace([np.inf],inf_fill_value)
    
    if label_name is not None:
        label_name = gnn_info[label_name]

    if return_data_labels_split:
        if label_name is not None:
            if type(label_name) != tuple:
                label_name = list(nu.convert_to_array_like(label_name))
            y = df[list(label_name)].to_numpy()
            x = pu.delete_columns(df,label_name)
            
            if y.ndim > 1: #have to convert it back from one hot encoding
                if add_negative_label:
                    #print(f"Adding negative label")
                    new_col = np.zeros((y.shape[0],1))
                    y = np.hstack([new_col,y])
                y = np.argmax(y,axis = 1)
        else:
            y = None
            x = df
            
        

        return x.to_numpy(),y
    else:
        return df

def feature_df_from_adj_feature_dict(adj_feature_dict):
    if "pandas" not in str(type(adj_feature_dict["feature_matrix"])):
        df = pd.DataFrame(adj_feature_dict["feature_matrix"])
        df.columns = adj_feature_dict["features"]
        df["node"] = adj_feature_dict["nodelist"]
    else:
        df = adj_feature_dict["feature_matrix"]
        
    return df

def G_from_adj_feature_dict(
    adj_feature_dict=None,
    filepath = None,
    plot = False,
    verbose = False
    ):
    """
    Purpose: To recover the original graph
    stored in the adjacency dict information
    
    Ex: 
    import neuron_nx_io as nxio
    G_rec = nxio.G_from_adj_feature_dict(
        filepath = filepaths[1],
        plot = True,
        verbose = True
        )
    """
    
    if adj_feature_dict is None:
        if verbose:
            print(f"Reading from {filepath}")
        adj_feature_dict = su.decompress_pickle(filepath)

    df = nxio.feature_df_from_adj_feature_dict(adj_feature_dict)
        
    
    G = xu.G_from_adjacency_matrix(
    matrix = adj_feature_dict["adjacency"],
    nodelist = adj_feature_dict["nodelist"],
    plot = True,
    )
    
    G = xu.set_node_attributes_from_df(G,df,index_name="node")
    
    if verbose:
        print("label_name,graph_label = ",(adj_feature_dict["label_name"],adj_feature_dict["graph_label"]))
    return G



# ----------------- exporting different types of graph attributes for GNNs -----------
def GNN_info_axon_vs_dendrite(
    G,
    distance_threshold = 100_000,
    distance_threshold_min = None,
    
    remove_starter_branches = True,
    divide_into_limbs = False,
    label_name = "axon_label",
    graph_label = None,
    
    return_filepaths = False,
    folder = "./Axon_vs_Dendrite/",
    description = "ax_vs_dendr",
    verbose = False,
    
    **kwargs
    ):
    
    
    features_to_output = [
        "mesh_volume",
        "n_spines",
        "total_spine_volume",
        "n_synapses_post",
        "n_synapses_pre",
        #"n_synapse_head",
        #"parent_skeletal_angle",
        "skeletal_length",
        "skeleton_vector_upstream_theta",
        "skeleton_vector_upstream_phi",
        "skeleton_vector_downstream_theta",
        "skeleton_vector_downstream_phi",
        "width_upstream",
        "width_no_spine",
        "width_downstream",
        "axon_label"
        ]
    
    #print(f"return_filepaths =- {return_filepaths}")
    
    filepaths = nxio.export_GNN_info_dict(
            G,
            features_to_output=features_to_output,
            remove_starter_branches = remove_starter_branches,
            divide_into_limbs = divide_into_limbs,

            label_name = label_name,#"axon_label",
            graph_label = graph_label,

            distance_threshold = distance_threshold,
            distance_threshold_min = distance_threshold_min,

            #output file features
            folder = folder,
            description = description,
            verbose = verbose,
        
            return_filepaths = return_filepaths,
            **kwargs

            )
    
    
    return filepaths
    
    
def GNN_info_compartment_proof(
    G,
    distance_threshold = None,
    distance_threshold_min = None,
    
    remove_starter_branches = True,
    divide_into_limbs = False,
    label_name = ("axon_label","basal_label","apical_label",),#"dendrite_label"),
    
    graph_label = None,
    
    return_filepaths = False,
    folder = "./Compartments_Proof/",
    description = "compartment_proof",
    verbose = False,
    
    **kwargs
    ):
    
    
    features_to_output = [
        "mesh_volume",
        "n_spines",
        "total_spine_volume",
        "n_synapses_post",
        "n_synapses_pre",
        "n_synapses_head",
        "n_synapses_neck",
        #"parent_skeletal_angle",
        "skeletal_length",
        "skeleton_vector_upstream_theta",
        "skeleton_vector_upstream_phi",
        "skeleton_vector_downstream_theta",
        "skeleton_vector_downstream_phi",
        "width_upstream",
        "width_no_spine",
        "width_downstream",
        "axon_label",
        #"dendrite_label",
        "basal_label",
        "apical_label",
        ]
    
    filepaths = nxio.export_GNN_info_dict(
    G,
    features_to_output=features_to_output,
    remove_starter_branches = remove_starter_branches,
    divide_into_limbs = divide_into_limbs,

    label_name = label_name,#"axon_label",
    graph_label = graph_label,
    
    distance_threshold = distance_threshold,
    distance_threshold_min=distance_threshold_min,
    
    #output file features
    folder = folder,
    description = description,
    verbose = verbose,
        
    return_filepaths = return_filepaths,
    
    )
    
    return filepaths


def GNN_info_merge_errors(
    G,
    distance_threshold = None,
    distance_threshold_min = None,
    remove_starter_branches = True,
    divide_into_limbs = False,
    #label_name = "auto_proof_filter_label",
    label_name = ("merge_clean","merge_high_degree_branching_label",
        "merge_low_degree_branching_label",
        "merge_width_jump_up_axon_label",
        "merge_axon_on_dendrite_label",
        "merge_high_degree_branching_dendrite_label",
        "merge_width_jump_up_dendrite_label",
        "merge_double_back_dendrite_label",),
    graph_label = None,

    axon_dendrite = None,
    
    return_filepaths = False,
    folder = "./Merge_Errors/",
    description = "merge_errors",
    
    
    verbose = False,
    
    **kwargs
    ):
    
    features_to_output = [
        "mesh_volume",
        "n_spines",
        "total_spine_volume",
        "n_synapses_post",
        "n_synapses_pre",
        "n_synapses_head",
        "n_synapses_neck",
        #"parent_skeletal_angle",
        "skeletal_length",
        "skeleton_vector_upstream_theta",
        "skeleton_vector_upstream_phi",
        "skeleton_vector_downstream_theta",
        "skeleton_vector_downstream_phi",
        "width_upstream",
        "width_no_spine",
        "width_downstream",
        "min_dist_synapses_pre_downstream_clip",
        "min_dist_synapses_pre_upstream_clip",
        
    ]
    
    if type(label_name) == str:
        features_to_output.append(label_name)
    else:
        features_to_output += label_name

    
    filepaths = nxio.export_GNN_info_dict(
        G,
        features_to_output=features_to_output,
        remove_starter_branches = remove_starter_branches,
        divide_into_limbs = divide_into_limbs,

        label_name = label_name,#"axon_label",
        graph_label = graph_label,

        distance_threshold = distance_threshold,
        distance_threshold_min=distance_threshold_min,

        #output file features
        folder = folder,
        description = description,
        verbose = verbose,

        axon_dendrite = axon_dendrite,
        return_filepaths = return_filepaths
        )
    
    return filepaths


def GNN_info_cell_type_fine(
    G,
    distance_threshold = None,
    distance_threshold_min=None,

    remove_starter_branches = True,
    divide_into_limbs = False,
    label_name = None,
    graph_label = None,

    axon_dendrite = "dendrite",
    
    return_filepaths = False,
    folder = "./Cell_Type_Fine/",
    description = "cell_type_fine",
    
    
    verbose = False,
    
    **kwargs
    ):
    
    features_to_output = [
        "mesh_volume",
        "n_spines",
        "total_spine_volume",
        "n_synapses_post",
        "n_synapses_pre",
        "n_synapses_head",
        "n_synapses_neck",
        #"parent_skeletal_angle",
        "skeletal_length",
        "skeleton_vector_upstream_theta",
        "skeleton_vector_upstream_phi",
        "skeleton_vector_downstream_theta",
        "skeleton_vector_downstream_phi",
        "width_upstream",
        "width_no_spine",
        "width_downstream",
        #"axon_label",
        #"dendrite_label",
        "basal_label",
        "apical_label"
        ]
    
    filepaths = nxio.export_GNN_info_dict(
        G,
        features_to_output=features_to_output,
        remove_starter_branches = remove_starter_branches,
        divide_into_limbs = divide_into_limbs,

        label_name = label_name,#"axon_label",
        graph_label = graph_label,

        distance_threshold = distance_threshold,
        distance_threshold_min=distance_threshold_min,

        #output file features
        folder = folder,
        description = description,
        verbose = verbose,

        axon_dendrite = axon_dendrite,
        return_filepaths = return_filepaths,
        **kwargs
        )
    
    return filepaths


# ------------ For the simplified version of Gnn CODE -------------
def compressed_dict_from_G(
    G,
    features = None,
    graph_identifiers = (
        "segment_id",
        "split_index",
        "nucleus_id",
        "external_layer"),
    dense_adjacency = True,
    data_name = "data"
    ):
    
    g_atts = xu.graph_attr_dict(G)
    curr_dict = {k:g_atts[k] for k in graph_identifiers}
    curr_dict[data_name] = xu.adjacency_feature_info(
        G,
        return_df_for_feature_matrix = False,
        feature_matrix_dtype = "float",
        dense_adjacency=dense_adjacency,
        features=features
    )
    
    return curr_dict

import numpy_utils as nu
import copy
def combine_limb_graph_data(
    graph_data,
    limb_idx,
    return_cluster_matrix = True,
    flat_cluster_matrix = True,
    verbose = False,
    max_nodes = 250,
    max_limbs = 25,
    limb_attributes_to_add = None,
    ):

    all_graph_data = copy.deepcopy(graph_data)

    n_nodes = np.sum([len(k["data"]["nodelist"]) for k in all_graph_data ])
    
    if verbose:
        print(f"n_nodes = {n_nodes}")

    node_count = 0
    nodelist = []
    adjacency_edges = []
    features_list = []
    all_edges = 0


    big_adj = np.zeros((n_nodes,n_nodes)).astype('int')
    
    if not flat_cluster_matrix:
        clust_matrix = np.zeros((max_limbs,max_nodes)).astype("int")
    else:
        clust_matrix = np.zeros(n_nodes).astype("int")

    for j,l_idx in enumerate(limb_idx):
        g = all_graph_data[j]["data"]
        curr_n_nodes = len(g["nodelist"])


        adj_matrix = g["adjacency"]
        big_adj[node_count:node_count+curr_n_nodes,node_count:node_count+curr_n_nodes] = adj_matrix

        if verbose:
            print(node_count,node_count+curr_n_nodes)
            print(f"adj_matrix = \n{adj_matrix}")

        curr_features = g["feature_matrix"]
        if limb_attributes_to_add is not None:
            curr_array = np.array([v[j] for v in limb_attributes_to_add.values()])
            features_values = np.tile(
                curr_array,
                (len(curr_features),1)
            )
            #print(f"curr_features.shape ={curr_features.shape}")
            curr_features = np.hstack([curr_features,features_values])


        features_list.append(curr_features)
        nodelist.append(g["nodelist"])

        if not flat_cluster_matrix:
            clust_matrix[j,node_count:node_count+curr_n_nodes] = 1/curr_n_nodes
        else:
            clust_matrix[node_count:node_count+curr_n_nodes] = j
            
        node_count += curr_n_nodes

    nodelist = np.hstack(nodelist)
    features_list = np.vstack(features_list)
    
    
    new_graph_data = all_graph_data[0].copy()
    fnames = new_graph_data["data"]["features"]
    if limb_attributes_to_add is not None:
        features_names = list(limb_attributes_to_add.keys())
        fnames += features_names
    

    # put back into one giant graph data
    
    new_graph_data["data"]["feature_matrix"] = nu.replace_nan_with_zero(features_list)
    new_graph_data["data"]["nodelist"] = nodelist
    new_graph_data["data"]["adjacency"] = big_adj
    new_graph_data["data"]["features"] = fnames
    
    if return_cluster_matrix:
        return new_graph_data,clust_matrix
    else:
        return new_graph_data
    
    
    
from tqdm_utils import tqdm
import neuron_nx_io as nxio
import pandas as pd

def neuron_df_for_train_from_limb_df(
    df,
    sort_attributes = None,#("soma_start_angle_max",)
    limb_attributes_to_add_to_branches = (
        "soma_start_angle_max",
        "max_soma_volume",
        "n_syn_soma"
        ),
    
    add_pool_suffix = True,
    
    node_weight_name = "skeletal_length",
    edge_weight = False,
    edge_weight_method = "max",
    
    
    #--- for hierarchical ---
    export_pool1_clusters = True,
    
    hierarchical = False,
    attributes_pool1 = ("soma_start_angle_max",),
    attributes_pool1_extra = None,
    attributes_pool2 = (
        "max_soma_volume",
        "n_syn_soma",
    ),
    graph_type = "binary_tree",#"complete_graph"
    verbose =False,
    ):
    
    if attributes_pool1 is not None:
        attributes_pool1 = list(attributes_pool1)
    else:
        attributes_pool1 = []
    
    if attributes_pool2 is not None:
        attributes_pool2 = list(attributes_pool2)
    else:
        attributes_pool2 = []

    if hierarchical:
        limb_attributes_to_add_to_branches = np.setdiff1d(
            limb_attributes_to_add_to_branches,np.union1d(attributes_pool1,attributes_pool2)
        )
    
    unique_seg_split = pu.filter_to_first_instance_of_unique_column(
        df[["segment_id","split_index"]],
        column_name=["segment_id","split_index"]
    )
    
    if edge_weight:
        add_self_loops = True
    else:
        add_self_loops = False

    new_dicts = []
    segs_splits = unique_seg_split.index.to_numpy()
    for segment_id,split_index in tqdm(segs_splits):
        curr_df = df.query(f"(segment_id=={segment_id}) and (split_index == {split_index})")

        if sort_attributes is not None:
            curr_df = pu.sort_df_by_column(
                curr_df,
                columns=sort_attributes)

        limb_idx = curr_df["limb_idx"].to_numpy()    

        if limb_attributes_to_add_to_branches is not None and len(limb_attributes_to_add_to_branches) > 0:
            limb_attributes_to_add = {
                f:curr_df[f].to_numpy() for f in limb_attributes_to_add_to_branches
            }
        else:
            limb_attributes_to_add = None

        graph_data,clust_matrix = nxio.combine_limb_graph_data(
            graph_data = curr_df["graph_data"].to_list(),
            limb_idx = limb_idx,
            limb_attributes_to_add=limb_attributes_to_add
        )
        
        if add_pool_suffix or hierarchical:
            suffix = "_pool0"
        else:
            suffix = ""

        ex_dict = pu.df_to_dicts(curr_df.iloc[:1,:])[0]
        ex_dict[f"names{suffix}"] = graph_data["data"]["nodelist"]
        ex_dict[f"x_features{suffix}"] = graph_data["data"]["features"]
        ex_dict[f"x{suffix}"] = graph_data["data"]["feature_matrix"]
        ex_dict[f"edge_index{suffix}"] = nu.edge_list_from_adjacency_matrix(
            graph_data["data"]["adjacency"],
            add_self_loops=add_self_loops)
        
        sk_length_idx = np.where(np.array(ex_dict[f"x_features{suffix}"]) == node_weight_name)[0][0]
        weight_values = ex_dict[f"x{suffix}"][:,sk_length_idx].astype("float")
        
        if node_weight_name is not None:
            ex_dict[f"node_weight{suffix}"] = weight_values
            
        if edge_weight:
            if len(ex_dict[f"edge_index{suffix}"]) > 0:
                ex_dict[f"edge_weight{suffix}"] = getattr(np,edge_weight_method)(
                    weight_values[ex_dict[f"edge_index{suffix}"]],axis=1
                ).astype("float")
            else:
                ex_dict[f"edge_weight{suffix}"] = np.array([]).astype('float')
            
            
        if hierarchical or export_pool1_clusters:
            ex_dict["pool1_names"] = limb_idx
            ex_dict["pool1"] = clust_matrix

        # ---- adding on all of the extra components for heirarchical pooling ------
        
        if hierarchical:
            
            if len(attributes_pool1) > 0:
                shape = (-1,len(attributes_pool1))
            else:
                shape = (1,0)
            ex_dict["x_pool1"] = curr_df[attributes_pool1].to_numpy().reshape(*shape)
            ex_dict["x_features_pool1"] =  attributes_pool1
            ex_dict["edge_index_pool1"] = xu.edge_list_from_graph_type(
                n=len(limb_idx),
                graph_type=graph_type,
                plot=False,
                add_self_loops=add_self_loops,
            )
            
            weight_values = curr_df[node_weight_name].to_numpy().astype("float")
        
            if node_weight_name is not None:
                ex_dict[f"node_weight_pool1"] = weight_values

            if edge_weight:
                if len(ex_dict[f"edge_index_pool1"]) > 0:
                    ex_dict[f"edge_weight_pool1"] = getattr(np,edge_weight_method)(
                        weight_values[ex_dict[f"edge_index_pool1"]],axis=1
                    ).astype("float")
                else:
                    ex_dict[f"edge_weight_pool1"] = np.array([]).astype('float')
            
            # adding on extra features to carry with
            if attributes_pool1_extra is not None:
                shape = (-1,len(attributes_pool1_extra))
                ex_dict["x_pool1_extra"] = curr_df[attributes_pool1_extra].to_numpy().reshape(*shape)
                ex_dict["x_features_pool1_extra"] =  attributes_pool1_extra
            

            #ex_dict["x_pool2"] = curr_df[attributes_pool2].to_numpy()
            if len(attributes_pool2) > 0:
                shape = (-1,len(attributes_pool2))
            else:
                shape = (1,0)
            ex_dict["x_pool2"] = curr_df[attributes_pool2].iloc[0,:].to_numpy().reshape(*shape)
            ex_dict["x_features_pool2"] =  attributes_pool2
            
            
        del ex_dict["graph_data"]

        new_dicts.append(ex_dict)


    df_with_labels = pd.DataFrame.from_records(new_dicts)
    return df_with_labels


import neuron_nx_io as nxio