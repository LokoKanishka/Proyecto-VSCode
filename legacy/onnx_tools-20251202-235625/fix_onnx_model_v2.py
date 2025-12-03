import onnx
from onnx import helper, TensorProto

def fix_onnx_model(model_path, output_path):
    model = onnx.load(model_path)
    graph = model.graph

    # The input is 'float_input' with shape [None, 1, 96] (or similar)
    # The LinearClassifier expects 2D.
    # We need to insert a Reshape node.

    # 1. Rename the original input of the LinearClassifier to something else
    # Find the node that uses 'float_input'
    linear_node = None
    for node in graph.node:
        if 'float_input' in node.input:
            linear_node = node
            break
    
    if not linear_node:
        print("Could not find node using float_input")
        return

    # 2. Create a constant tensor for the new shape [-1, 1536] (or whatever features is)
    # Actually, we want to flatten the last two dims if it's [batch, 1, features] -> [batch, features]
    # Or just reshape to [batch, -1]
    
    # Let's check the input dimension from the graph input
    input_tensor = graph.input[0]
    dims = [d.dim_value for d in input_tensor.type.tensor_type.shape.dim]
    print(f"Original Input Dims: {dims}") # e.g. [0, 1, 1536] where 0 is None
    
    feature_dim = dims[2]
    
    # Create shape constant
    shape_const_name = "reshape_shape"
    shape_const = helper.make_tensor(
        shape_const_name,
        TensorProto.INT64,
        [2],
        [-1, feature_dim]
    )
    
    # Add the constant node to the graph
    shape_node = helper.make_node(
        "Constant",
        inputs=[],
        outputs=[shape_const_name],
        value=shape_const
    )
    graph.node.insert(0, shape_node)

    # 3. Create the Reshape node
    # Input: float_input, shape_const
    # Output: float_input_reshaped
    reshape_node = helper.make_node(
        "Reshape",
        inputs=["float_input", shape_const_name],
        outputs=["float_input_reshaped"],
        name="InputReshape"
    )
    graph.node.insert(1, reshape_node)

    # 4. Update LinearClassifier to use float_input_reshaped
    # We need to replace 'float_input' in linear_node.input with 'float_input_reshaped'
    new_inputs = []
    for inp in linear_node.input:
        if inp == 'float_input':
            new_inputs.append('float_input_reshaped')
        else:
            new_inputs.append(inp)
    
    linear_node.input[:] = new_inputs

    # Save
    onnx.save(model, output_path)
    print(f"Fixed model saved to {output_path}")

if __name__ == "__main__":
    fix_onnx_model("lucy_voice/data/wakeword/modelos/hola_lucy.onnx", "lucy_voice/data/wakeword/modelos/hola_lucy_fixed.onnx")
