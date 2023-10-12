from flask import Flask, request, jsonify
from flask_pymongo import PyMongo
from flask_cors import CORS  # Import CORS from flask_cors

# venv\Scripts\activate to activate the server 
# python  server.py to run it


app = Flask(__name__)
CORS(app) 

# app.config["MONGO_URI"] = "mongodb://localhost:27017/testing"
# mongo = PyMongo(app)

# Update your MongoDB URI with your MongoDB Atlas connection string
# Replace the placeholder with your actual connection string
app.config["MONGO_URI"] = "mongodb+srv://matet2501:heihei2501@cluster0.mfdvoch.mongodb.net/testing?retryWrites=true&w=majority"
mongo = PyMongo(app)


# Endpoint for creating a new patient record
@app.route('/api/generate_patients', methods=['POST'])
def create_patient():
    data = request.json  # Get the JSON data from the request

    # Insert the patient data into the MongoDB collection
    patient_id = mongo.db.patients.insert_one(data).inserted_id

    # Extract firstName and lastName from the data
    firstName = data.get('patientFirstName', '')
    lastName = data.get('patientLastName', '')

    # Combine firstName and lastName to create the name field
    name = firstName + ' ' + lastName


     # Initialize the patientInfo object
    patientInfo = {
        'name': name,
        'patientTaskList': {}
    }

    # Insert the patientInfo into the "tasklist" collection within the same database
    tasklist_id = mongo.db.tasklist.insert_one(patientInfo).inserted_id

    return jsonify({
        "message": "Patient and patientInfo created successfully",
        "patient_id": str(patient_id),
        "tasklist_id": str(tasklist_id)
    })


    


@app.route('/api/get_patients', methods=['GET'])
def get_patients():
    print("get Patient")
    # Fetch all patient records from the "patient" collection
    patients = list(mongo.db.patients.find({}, {"_id": 0}))  # Exclude "_id" field from the response
    
    return jsonify({"data": patients})


@app.route('/api/add_task', methods=['POST'])
def add_patient_task():
    print("add tasks")
    try:
        data = request.json  # Get the JSON data from the request
        print(data)
        # Extract the necessary data from the request body
        patient_name = data.get('patientName', '')
        task_date = data.get('taskDate', '')
        task_data = data.get('taskData', {})
        
        # Find the patient by name
        patient = mongo.db.tasklist.find_one({'name': patient_name})

        if patient:
            patientTaskList = patient['patientTaskList']
            
            if task_date not in patientTaskList:
                patientTaskList[task_date] = []  # Initialize the list if it doesn't exist
                print("made array")
            
            # Generate a unique task id
            max_id = 1  # Set the default ID to 1
            
            if patientTaskList[task_date]:
                max_id = max(task['id'] for task in patientTaskList[task_date]) + 1
            
            task_data['id'] = max_id
            
            patientTaskList[task_date].append(task_data)  # Append the new task_data to the list
            
            # Update the patient's task list in the "tasklist" collection
            result = mongo.db.tasklist.update_one(
                {'name': patient_name},
                {'$set': {'patientTaskList': patientTaskList}}
            )

            if result.modified_count == 1:
                return jsonify({'message': 'Task added successfully'})
            else:
                return jsonify({'error': 'Task could not be added'})

        else:
            return jsonify({'error': 'Patient not found'})

    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/get_tasks', methods=['GET'])
def get_task_list():
    print("gettin task list")
    try:
        date = request.args.get('date')
        print(date)
        first_name = request.args.get('firstName')
        last_name = request.args.get('lastName')
        full_name = f"{first_name} {last_name}"

        # Find the patient by name
        patient = mongo.db.tasklist.find_one({'name': full_name})
        print(patient)
        if patient:
            patient_task_list = patient.get('patientTaskList', {})
            tasks_for_date = patient_task_list.get(date, [])

            return jsonify({"tasks": tasks_for_date}), 200
        else:
            return jsonify({"error": "Patient not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/delete_task', methods=['POST'])
def delete_task():
    print("delete")
    try:
        data = request.get_json()
        patient_name = data.get('patientName')
        task_name = data.get('taskName')
        task_time = data.get('taskTime')

        # Get the tasklist collection from MongoDB
        tasklist = mongo.db.tasklist

        # Find the document with the matching patient name
        result = tasklist.find_one({'name': patient_name})

        if result:
            # Initialize a variable to keep track of whether a task was deleted
            task_deleted = False

            # Iterate through the patient's task dates
            for task_date, tasks in result['patientTaskList'].items():
                # Filter the tasks to find the one with matching name and time
                updated_tasks = [task for task in tasks if task['task'] != task_name or task['time'] != task_time]

                # Check if a task was removed
                if len(updated_tasks) < len(tasks):
                    # Update the document in MongoDB with the new task list
                    tasklist.update_one(
                        {'name': patient_name},
                        {'$set': {'patientTaskList.' + task_date: updated_tasks}}
                    )
                    task_deleted = True

                if not updated_tasks:
                    tasklist.update_one(
                        {'name': patient_name},
                        {'$unset': {'patientTaskList.' + task_date: ''}}
                    )

                    

            if task_deleted:
                return jsonify({'message': 'Task deleted successfully'}), 200
            else:
                return jsonify({'message': 'Task not found'}), 404

        return jsonify({'message': 'Patient not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@app.route('/api/update_task', methods=['POST'])
def update_task():
    try:
        
        data = request.json
        print(data)
        # Extract the task ID, patient name, and task date from the request data
        task_id = data['taskId']
        patient_name = data['patientName']
        task_date = data['taskDate']

        # Find the patient's task list for the given date
        task_list = mongo.db.tasklist.find_one({'name': patient_name})
        if task_list and task_date in task_list['patientTaskList']:
            tasks = task_list['patientTaskList'][task_date]
            print(tasks)
            for task in tasks:
                if task['id'] == task_id:
                    # Toggle the completion status
                    task['completed'] = not task['completed']
                    print("changed")

            # Update the task list in the MongoDB collection
            result = mongo.db.tasklist.update_one({'name': patient_name}, {'$set': {'patientTaskList': task_list['patientTaskList']}})

            if result.modified_count > 0:
                # Return the updated task list for the date
                updated_tasks = task_list['patientTaskList'][task_date]
                print(update_task)
                return jsonify({'message': 'Task completion status toggled successfully', 'updatedTasks': updated_tasks}), 200
            else:
                return jsonify({'message': 'Task not found or not toggled'}), 404

        return jsonify({'message': 'Patient or task date not found'}), 404

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/get_task_options', methods=['GET'])
def get_task_options():
    # Fetch preset tasks from MongoDB collection
    preset_tasks = list(mongo.db.presetTask.find({}, {'_id': 0}))
    
    return jsonify(preset_tasks)



@app.route('/api/get_patient_info', methods=['GET'])
def get_patient_info():
    print("Getting Patient Info")
    
    date = request.args.get('date')
    print(date)
    first_name = request.args.get('firstName')
    last_name = request.args.get('lastName')
    full_name = f"{first_name} {last_name}"

    # Find the patient by name
    patient = mongo.db.patients.find_one({'patientFirstName': first_name, 'patientLastName': last_name})
    
    if patient:
        # Convert the ObjectId to a string
        patient.pop('_id', None)
        return jsonify({"patientProfile": patient}), 200
    else:
        return jsonify({'error': 'Patient not found'}), 404
    
            
@app.route('/api/add_care_note', methods=['POST'])
def add_care_notes():
    # Get the JSON data from the request
    request_data = request.get_json()
    print(request_data)
    if not request_data:
        print("here")
        return jsonify({'error': 'Invalid data'}), 400
        
    patient_name = request_data.get('patientName')
    note_date = request_data.get('date')
    note_time = request_data.get('time')
    note_text = request_data.get('careNote')
    username = request_data.get('username')

    if not patient_name or not note_date or not note_time or not note_text or not username:
        return jsonify({'error': 'Incomplete data'}), 400

    # Define a care note structure
    care_note = {
        'time': note_time,
        'note': note_text,
        'username': username
    }

    # Create a new care note entry
    new_entry = {
        'patient_name': patient_name,
        'carenote': {
            note_date: [care_note]  # Initialize the date with a list containing the care note
        }
    }
    

    care_notes_collection  = mongo.db.careNotes
    
    # Check if a document for the patient already exists
    existing_entry = care_notes_collection.find_one({'patient_name': patient_name})

    if existing_entry:
        # Document already exists, add or update the care note
        care_notes = existing_entry['carenote']
        if note_date in care_notes:
            care_notes[note_date].append(care_note)  # Add a new care note to the existing date
        else:
            care_notes[note_date] = [care_note]  # Create a new date entry
        care_notes_collection.update_one({'patient_name': patient_name}, {'$set': {'carenote': care_notes}})
    else:
        # Document doesn't exist, create a new document
        care_notes_collection.insert_one(new_entry)

    return jsonify({'message': 'Care note added to MongoDB'}), 200    


@app.route('/api/get_past_care_notes', methods=['GET'])
def get_past_care_notes():
    # Get the patient name and date from the query parameters
    patient_name = request.args.get('patientName')
    date = request.args.get('date')
    care_notes_collection = mongo.db.careNotes
    print(date)

    # Find the patient by name
    patient = care_notes_collection.find_one({'patient_name': patient_name})
    # print(patient)

    if patient:
        # Retrieve the care notes for the specified date
        care_notes_for_date = patient['carenote'].get(date, [])

        
        if care_notes_for_date:
            # Return the care notes for the specified date
            return jsonify(care_notes_for_date) , 200
        else:
            return jsonify({'error': f'No care notes found for {patient_name} on {date}'}), 200
    else:
        return jsonify({'error': f'Patient {patient_name} not found'}), 404

@app.route('/api/edit_existing_task', methods=['POST'])
def edit_existing_task():
    print("editing existing data")
    try:
        data = request.json
        task_id = data['taskID']
        patient_name = data['patientName']
        task_date = data['taskDate']
        comments = data.get('comments', '')  # Use data.get() to get comments as an optional field

        print(data)
        # Find the patient document by patient name
        collection = mongo.db.tasklist
        patient = collection.find_one({'name': patient_name})
        print(patient)
        if patient:
            # Check if the task date exists in the patientTaskList
            if task_date in patient['patientTaskList']:
                tasks = patient['patientTaskList'][task_date]

                # Find the task to update based on task_id
                for task in tasks:
                    if task['id'] == task_id:
                        # Update the task and comments
                        task['comments'] = comments  
                        # Save the updated patient document back to the database
                        collection.update_one({'name': patient_name}, {'$set': {'patientTaskList': patient['patientTaskList']}})
                        return jsonify({'message': 'Task updated successfully'}), 200

        return jsonify({'message': 'Patient or task not found'}), 404

    except Exception as e:
        return jsonify({'error': str(e)}), 500





if __name__ == '__main__':
    app.run(debug=True)


