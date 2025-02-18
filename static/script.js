document.addEventListener("DOMContentLoaded", function () {
    /***** Generic Section Toggle Functions *****/


    
    
    // Expose functions globally so inline onclick attributes can use them.
    window.addSection = function (sectionId) {
        var section = document.getElementById(sectionId);
        if (section) {
            section.style.display = "block"; // Show the section

            // Re-enable the inputs inside the section when shown
            var inputs = section.querySelectorAll("input[required], textarea[required], select[required]");
            inputs.forEach(function(input) {
                input.disabled = false; // Enable the input
                input.setAttribute("required", true); // Add required attribute back
            });

            // Special case for practical periods section
            if (sectionId === "practical_periods_section") {
                document.getElementById("practical_periods").disabled = false;
                document.getElementById("practical_periods").setAttribute("required", true);
            }
        }
    };

    window.removeSection = function (sectionId) {
        var section = document.getElementById(sectionId);
        if (section) {
            section.style.display = "none"; // Hide the section

            // Disable the inputs inside the section when hidden
            var inputs = section.querySelectorAll("input[required], textarea[required], select[required]");
            inputs.forEach(function(input) {    
                input.disabled = true; // Disable the input
                input.removeAttribute("required"); // Remove the required attribute
            });

            // Special case for practical periods section
            if (sectionId === "practical_periods_section") {
                document.getElementById("practical_periods").disabled = true;
                document.getElementById("practical_periods").removeAttribute("required");
            }

            // Add to removed sections (hidden input)
            var removedSections = document.getElementById("removed_sections");
            var sections = removedSections.value.split(",");
            if (!sections.includes(sectionId)) {
                sections.push(sectionId);
            }
            removedSections.value = sections.join(",");
        }
    };
    var addExperimentBtn = document.getElementById("addexperiments");

    if (addExperimentBtn) {
        addExperimentBtn.addEventListener("click", function () {
            var experimentsDiv = document.getElementById("experimentsFields"); // ✅ Correct ID
            var newIndex = experimentsDiv.querySelectorAll("input[name='experiments']").length + 1;
    
            var experimentDiv = document.createElement("div");
            experimentDiv.className = "experiment-item";
    
            var newInput = document.createElement("input");
            newInput.type = "text";
            newInput.name = "experiments"; // ✅ Consistent with HTML name attribute
            newInput.placeholder = "Experiment " + newIndex;
            newInput.required = true;
    
            var removeBtn = document.createElement("button");
            removeBtn.type = "button";
            removeBtn.className = "remove-btn";
            removeBtn.innerText = "Remove";
            removeBtn.onclick = function () {
                experimentDiv.remove();
            };
    
            experimentDiv.appendChild(newInput);
            experimentDiv.appendChild(removeBtn);
            experimentsDiv.appendChild(experimentDiv);
        });
    }
    


    /***** Course Objectives Dynamic Input *****/
    var addObjectiveBtn = document.getElementById("addObjective");
    if (addObjectiveBtn) {
        addObjectiveBtn.addEventListener("click", function () {
            var objectivesDiv = document.getElementById("objectiveFields");
            var newIndex = objectivesDiv.querySelectorAll("input[name='objective']").length + 1;

            var objectiveDiv = document.createElement("div");
            objectiveDiv.className = "objective-item";

            var newInput = document.createElement("input");
            newInput.type = "text";
            newInput.name = "objective";
            newInput.placeholder = "Objective " + newIndex;
            newInput.required = true;

            var removeBtn = document.createElement("button");
            removeBtn.type = "button";
            removeBtn.className = "remove-btn";
            removeBtn.innerText = "Remove";
            removeBtn.onclick = function () {
                objectiveDiv.remove();
            };

            objectiveDiv.appendChild(newInput);
            objectiveDiv.appendChild(removeBtn);
            objectivesDiv.appendChild(objectiveDiv);
        });
    }
    

    var addYouTubeBtn = document.getElementById("addYouTube");
let youtubeCount = 1; // Keep track of YouTube references

if (addYouTubeBtn) {
    addYouTubeBtn.addEventListener("click", function () {
        const youtubeFields = document.getElementById("youtubeFields");

        // Increment the YouTube reference count
        youtubeCount++;

        // Create a new YouTube reference div
        const youtubeDiv = document.createElement("div");
        youtubeDiv.className = "youtube-item";

        // Create the YouTube title input field
        const titleInput = document.createElement("input");
        titleInput.type = "text";
        titleInput.name = `youtube_title_${youtubeCount}`;
        titleInput.placeholder = `Video Title ${youtubeCount}`;
        titleInput.required = true;

        // Create the YouTube description textarea field
        const descTextarea = document.createElement("textarea");
        descTextarea.name = `youtube_desc_${youtubeCount}`;
        descTextarea.placeholder = `Video Description ${youtubeCount}`;
        descTextarea.required = true;

        // Create the YouTube URL input field
        const urlInput = document.createElement("input");
        urlInput.type = "text";
        urlInput.name = `youtube_url_${youtubeCount}`;
        urlInput.placeholder = `YouTube URL ${youtubeCount}`;
        urlInput.required = true;

        // Create the remove button for this reference
        const removeBtn = document.createElement("button");
        removeBtn.type = "button";
        removeBtn.className = "remove-btn";
        removeBtn.innerText = "Remove";
        removeBtn.onclick = function () {
            youtubeDiv.remove();
        };

        // Append the new input fields and button to the YouTube div
        youtubeDiv.appendChild(titleInput);
        youtubeDiv.appendChild(descTextarea);
        youtubeDiv.appendChild(urlInput);
        youtubeDiv.appendChild(removeBtn);

        // Append the new YouTube div to the youtubeFields container
        youtubeFields.appendChild(youtubeDiv);
    });
}





    /***** Course Units Dynamic Input *****/
    let unitCount = 1; // Initialize unit count

    // Function to add a new unit input field dynamically
    var addUnitBtn = document.getElementById("addUnit");
    if (addUnitBtn) {
        addUnitBtn.addEventListener("click", function () {
            const unitFields = document.getElementById("unitFields");

            // Increment the unit count
            unitCount++;

            // Create a new unit div
            const unitDiv = document.createElement("div");
            unitDiv.className = "unit-item";

            // Create the unit title input field
            const titleInput = document.createElement("input");
            titleInput.type = "text";
            titleInput.name = `unit_title_${unitCount}`; // Assign a unique name
            titleInput.placeholder = `Unit Title ${unitCount}`;
            titleInput.required = true; // Make it required

            // Create the unit content textarea field
            const contentTextarea = document.createElement("textarea");
            contentTextarea.name = `unit_content_${unitCount}`; // Assign a unique name
            contentTextarea.placeholder = `Unit Content ${unitCount}`;
            contentTextarea.required = true; // Make it required

            // Create the unit periods input field
            const periodsInput = document.createElement("input");
            periodsInput.type = "number";
            periodsInput.name = `unit_periods_${unitCount}`; // Assign a unique name
            periodsInput.placeholder = `No. of Periods ${unitCount}`;
            periodsInput.required = true;

            // Create the remove button for this unit
            const removeBtn = document.createElement("button");
            removeBtn.type = "button";
            removeBtn.className = "remove-btn";
            removeBtn.innerText = "Remove Unit";
            removeBtn.onclick = function () {
                unitDiv.remove();
            };

            // Append the new input fields and button to the unit div
            unitDiv.appendChild(titleInput);
            unitDiv.appendChild(contentTextarea);
            unitDiv.appendChild(periodsInput);
            unitDiv.appendChild(removeBtn);

            // Append the new unit div to the unitFields container
            unitFields.appendChild(unitDiv);
        });
    }

    /***** Course Outcomes Dynamic Input *****/
    var addOutcomeBtn = document.getElementById("addOutcome");
    if (addOutcomeBtn) {
        addOutcomeBtn.addEventListener("click", function () {
            var outcomesDiv = document.getElementById("outcomeFields");
            var newIndex = outcomesDiv.querySelectorAll("input[name='course_outcome']").length + 1;

            var outcomeDiv = document.createElement("div");
            outcomeDiv.className = "outcome-item";

            var newInput = document.createElement("input");
            newInput.type = "text";
            newInput.name = "course_outcome";
            newInput.placeholder = "CO" + newIndex;
            newInput.required = true;

            var removeBtn = document.createElement("button");
            removeBtn.type = "button";
            removeBtn.className = "remove-btn";
            removeBtn.innerText = "Remove";
            removeBtn.onclick = function () {
                outcomeDiv.remove();
            };

            outcomeDiv.appendChild(newInput);
            outcomeDiv.appendChild(removeBtn);
            outcomesDiv.appendChild(outcomeDiv);
        });
    }

    /***** Textbooks Dynamic Input *****/
    var addTextbookBtn = document.getElementById("addTextbook");
    if (addTextbookBtn) {
        addTextbookBtn.addEventListener("click", function () {
            var textbooksDiv = document.getElementById("textbookFields");
            var newIndex = textbooksDiv.querySelectorAll("input[name='textbook']").length + 1;

            var textbookDiv = document.createElement("div");
            textbookDiv.className = "textbook-item";

            var newInput = document.createElement("input");
            newInput.type = "text";
            newInput.name = "textbook";
            newInput.placeholder = "Textbook " + newIndex;
            newInput.required = true;

            var removeBtn = document.createElement("button");
            removeBtn.type = "button";
            removeBtn.className = "remove-btn";
            removeBtn.innerText = "Remove";
            removeBtn.onclick = function () {
                textbookDiv.remove();
            };

            textbookDiv.appendChild(newInput);
            textbookDiv.appendChild(removeBtn);
            textbooksDiv.appendChild(textbookDiv);
        });
    }

    /***** References Dynamic Input *****/
    var addReferenceBtn = document.getElementById("addReference");
    if (addReferenceBtn) {
        addReferenceBtn.addEventListener("click", function () {
            var referencesDiv = document.getElementById("referenceFields");
            var newIndex = referencesDiv.querySelectorAll("input[name='reference']").length + 1;

            var referenceDiv = document.createElement("div");
            referenceDiv.className = "reference-item";

            var newInput = document.createElement("input");
            newInput.type = "text";
            newInput.name = "reference";
            newInput.placeholder = "Reference " + newIndex;
            newInput.required = true;

            var removeBtn = document.createElement("button");
            removeBtn.type = "button";
            removeBtn.className = "remove-btn";
            removeBtn.innerText = "Remove";
            removeBtn.onclick = function () {
                referenceDiv.remove();
            };

            referenceDiv.appendChild(newInput);
            referenceDiv.appendChild(removeBtn);
            referencesDiv.appendChild(referenceDiv);
        });
    }

    /***** Form Submission Validation (Skip Hidden Sections) *****/
    document.getElementById("courseForm").addEventListener("submit", function(event) {
        // Disable validation for fields in hidden sections
        var sectionsToValidate = ["courseObjectives", "courseDescription", "prerequisites", "courseUnits", "assessmentsGrading", "courseOutcomes", "textbooks", "references"];
        
        sectionsToValidate.forEach(function(sectionId) {
            var section = document.getElementById(sectionId);
            if (section.style.display === "none") {
                var inputs = section.querySelectorAll("input[required], textarea[required], select[required]");
                inputs.forEach(function(input) {
                    input.removeAttribute("required"); // Disable required validation for hidden fields
                });
            }
        });

        // Validate the form manually after removing "required" from hidden sections
        if (this.checkValidity() === false) {
            event.preventDefault();
            alert("Please fill in the required fields.");
        }
    });
});

