import onnx
from onnx import helper, TensorProto

model_path = "lucy_voice/data/wakeword/modelos/hola_lucy.onnx"
model = onnx.load(model_path)

# The current input is 'float_input' with shape [None, 1536]
# We want to change 'float_input' to have shape [None, 16, 96]
# And insert a Flatten node that takes 'float_input' and outputs 'flattened_input'
# Then rename the original input of the first node to 'flattened_input'

graph = model.graph

# 1. Find the original input
original_input = graph.input[0]
print(f"Original input: {original_input.name}")

# 2. Create the new input definition (3D)
# We keep the name 'float_input' for the external interface because openwakeword might use it?
# Actually, let's rename the internal usage first.

# Rename the input of the first node (LinearClassifier)
# We assume the first node is the classifier or a scaler.
# Let's find all nodes that use 'float_input'
for node in graph.node:
    for i, input_name in enumerate(node.input):
        if input_name == original_input.name:
            node.input[i] = "flattened_input"

# 3. Create the Flatten node
# Input: 'float_input' (the graph input)
# Output: 'flattened_input' (the internal tensor)
flatten_node = helper.make_node(
    "Flatten",
    inputs=[original_input.name],
    outputs=["flattened_input"],
    axis=1
)

# Insert the Flatten node at the beginning of the graph
graph.node.insert(0, flatten_node)

# 4. Update the graph input shape definition
# Change shape from [None, 1536] to [None, 16, 96]
# dim 0 is None (batch)
# dim 1 is 1536 -> change to 16
# dim 2 -> add 96

# Clear existing dims
original_input.type.tensor_type.shape.dim.pop() # pop 1536
original_input.type.tensor_type.shape.dim.pop() # pop None (if present)

# Rebuild dims
d0 = original_input.type.tensor_type.shape.dim.add()
# d0.dim_param = "batch" # Keep it undefined or use param
# Actually, let's just set it cleanly.

new_input = helper.make_tensor_value_info(
    original_input.name,
    TensorProto.FLOAT,
    [None, 16, 96]
)

# Replace the input in the graph
graph.input.remove(original_input)
graph.input.insert(0, new_input)

# 5. Save
onnx.save(model, model_path)
print(f"Model patched and saved to {model_path}")
