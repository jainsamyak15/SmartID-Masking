const idLabels = {
    'aadhaar': ['aadhaar_no', 'aadhaar_dob', 'aadhaar_gender', 'aadhaar_address', 'aadhaar_holder_name', 'aadhaar_localname', 'aadhaar_new', 'aadhaar_addressLocal'],
    'pan': ['pan_num', 'dob', 'father', 'name'],
    'voter': ['Relation_localname', 'address', 'age', 'date_of_issue', 'dob', 'elector_name', 'gender', 'local_address', 'localname', 'photo', 'place', 'relation_name', 'voter_id_no'],
    'passport': ['DOB', 'File_no', 'Surname', 'address', 'country_code', 'date_of_expiry', 'date_of_issue', 'details', 'father_name', 'mother_name', 'name', 'nationality', 'old_passport_details', 'passport_no', 'photo', 'place_of_birth', 'place_of_issue', 'sex', 'sign', 'spouse_name', 'type']
};

let currentCardType = null;

function createCheckboxes(labels) {
    const container = document.getElementById('labelCheckboxes');
    container.innerHTML = '';
    labels.forEach(label => {
        const checkboxWrapper = document.createElement('div');
        checkboxWrapper.className = 'checkbox-wrapper';

        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.id = label;
        checkbox.name = 'labels';
        checkbox.value = label;

        const labelElement = document.createElement('label');
        labelElement.htmlFor = label;
        labelElement.appendChild(document.createTextNode(label.replace(/_/g, ' ')));

        checkboxWrapper.appendChild(checkbox);
        checkboxWrapper.appendChild(labelElement);
        container.appendChild(checkboxWrapper);
    });
}

function showElement(id) {
    document.getElementById(id).classList.remove('hidden');
}

function hideElement(id) {
    document.getElementById(id).classList.add('hidden');
}

document.getElementById('uploadForm').addEventListener('submit', async function(event) {
    event.preventDefault();

    const formData = new FormData();
    const imageFile = document.getElementById('image').files[0];
    formData.append('image', imageFile);

    try {
        const cardTypeResponse = await fetch('/detect_card_type', {
            method: 'POST',
            body: formData
        });

        if (cardTypeResponse.ok) {
            const cardTypeData = await cardTypeResponse.json();
            currentCardType = cardTypeData.card_type;

            let cardTypeMessage = '';
            if (idLabels.hasOwnProperty(currentCardType)) {
                cardTypeMessage = `${currentCardType.toUpperCase()} Card Detected`;
                createCheckboxes(idLabels[currentCardType]);
                showElement('maskingOptions');
            } else {
                cardTypeMessage = 'Unknown Card Type';
                hideElement('maskingOptions');
                return;
            }

            document.getElementById('cardType').innerText = cardTypeMessage;
            showElement('result-section');
        } else {
            throw new Error('Card type detection failed');
        }
    } catch (error) {
        console.error('Error:', error);
        alert(error.message);
    }
});

document.getElementById('maskButton').addEventListener('click', async function() {
    const formData = new FormData();
    const imageFile = document.getElementById('image').files[0];
    formData.append('image', imageFile);
    formData.append('card_type', currentCardType);

    const selectedLabels = Array.from(document.querySelectorAll('input[name="labels"]:checked')).map(cb => cb.value);
    formData.append('labels', JSON.stringify(selectedLabels));

    try {
        const pidResponse = await fetch('/detect_pids', {
            method: 'POST',
            body: formData
        });

        if (pidResponse.ok) {
            const blob = await pidResponse.blob();
            const url = URL.createObjectURL(blob);
            document.getElementById('resultImage').src = url;
            showElement('imageWrapper');
        } else {
            throw new Error('PID detection and masking failed');
        }
    } catch (error) {
        console.error('Error:', error);
        alert(error.message);
    }
});

document.querySelector('.file-input-wrapper input[type=file]').addEventListener('change', function() {
    const fileName = this.files[0].name;
    this.nextElementSibling.textContent = fileName;
});

document.getElementById('refreshButton').addEventListener('click', function() {
    location.reload();
});