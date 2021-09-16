<template>
  <div>
    <h1 class="page-title" v-if="creatingNew"><span class="font-weight-light">Creating</span> new RelVal</h1>
    <h1 class="page-title" v-else><span class="font-weight-light">Editing RelVal</span> {{prepid}}</h1>
    <v-card raised class="page-card">
      <table v-if="editableObject">
        <tr>
          <td>PrepID</td>
          <td><input type="text" v-model="editableObject.prepid" :disabled="!editingInfo.prepid"></td>
        </tr>
        <tr>
          <td>Batch name (-b)</td>
          <td><input type="text" v-model="editableObject.batch_name" placeholder="E.g. fullsim_noPU_..." :disabled="!editingInfo.batch_name"></td>
        </tr>
        <tr>
          <td>CMSSW Release</td>
          <td><input type="text" v-model="editableObject.cmssw_release" placeholder="E.g. CMSSW_11_..." :disabled="!editingInfo.cmssw_release"></td>
        </tr>
        <tr>
          <td>CPU Cores (-t)</td>
          <td><input type="number" v-model="editableObject.cpu_cores" :disabled="!editingInfo.cpu_cores" min="1" max="8"></td>
        </tr>
        <tr>
          <td>Custom Fragment</td>
          <td>
            <pre style="font-size: 0.8em"><textarea style="white-space: pre" v-model="editableObject.fragment" :disabled="!editingInfo.fragment"></textarea></pre>
          </td>
        </tr>
        <tr>
          <td>Label (--label)</td>
          <td><input type="text" v-model="editableObject.label" placeholder="E.g. gcc8 or rsb or pmx" :disabled="!editingInfo.label"></td>
        </tr>
        <tr>
          <td>Matrix (--what)</td>
          <td>
            <select v-model="editableObject.matrix" :disabled="!editingInfo.matrix">
              <option>standard</option>
              <option>upgrade</option>
              <option>generator</option>
            </select>
          </td>
        </tr>
        <tr>
          <td>Memory</td>
          <td><input type="number" v-model="editableObject.memory" :disabled="!editingInfo.memory" min="0" max="32000" step="1000">MB</td>
        </tr>
        <tr>
          <td>Notes</td>
          <td><textarea v-model="editableObject.notes" placeholder="E.g. Goals, comments, links to TWiki and HN" :disabled="!editingInfo.notes"></textarea></td>
        </tr>
        <tr>
          <td>Sample Tag</td>
          <td><input type="text" v-model="editableObject.sample_tag" placeholder="E.g. Run2, Run3, Phase2, HIN, GEN, ..." :disabled="!editingInfo.sample_tag"></td>
        </tr>
        <tr>
          <td>Size per event</td>
          <td><input type="number" v-model="editableObject.size_per_event" :disabled="!editingInfo.size_per_event">kB</td>
        </tr>
        <tr v-if="editableObject.steps">
          <td>Steps ({{listLength(editableObject.steps)}})</td>
          <td>
            <div v-for="(step, index) in editableObject.steps" :key="index">
              <h3>Step {{index + 1}}</h3>
              <table>
                <tr>
                  <td>Name</td><td><input type="text" v-model="step.name" :disabled="!editingInfo.steps"></td>
                </tr>
                <tr>
                  <td>CMSSW Release</td><td><input type="text" v-model="step.cmssw_release" :disabled="!editingInfo.steps"></td>
                </tr>
                <tr>
                  <td>SCRAM Arch</td><td><input type="text" v-model="step.scram_arch" placeholder="If empty, uses default value of the release" :disabled="!editingInfo.steps"></td>
                </tr>
                <tr v-if="index == 0 && step.step_type != 'input'">
                  <td>Events per lumi</td><td><input type="text" v-model="step.events_per_lumi" :disabled="!editingInfo.steps"></td>
                </tr>
                <tr v-if="step.step_type != 'input'">
                  <td>Keep output</td><td><input type="checkbox" v-model="step.keep_output" :disabled="!editingInfo.steps"></td>
                </tr>
                <tr v-if="index != 0">
                  <td>Lumis per job</td><td><input type="text" v-model="step.lumis_per_job" :disabled="!editingInfo.steps"></td>
                </tr>
                <tr v-if="index == 0">
                  <td>RelVal Step type</td>
                  <td>
                    <input type="radio" class="mr-1" v-model="step.step_type" :name="'step' + index" :value="'input'" :disabled="!editingInfo.steps">Input dataset
                    <input type="radio" class="mr-1 ml-2" v-model="step.step_type" :name="'step' + index" :value="'driver'" :disabled="!editingInfo.steps">cmsDriver
                  </td>
                </tr>
                <template v-if="step.step_type == 'input'">
                  <tr>
                    <td>Dataset</td><td><input type="text" v-model="step.input.dataset" :disabled="!editingInfo.steps"></td>
                  </tr>
                  <tr>
                    <td>Label</td><td><input type="text" v-model="step.input.label" :disabled="!editingInfo.steps"></td>
                  </tr>
                  <tr>
                    <td>Lumisection ranges</td>
                    <td>
                      <input type="text" style="width: 75%;font-family: monospace;" v-model="step.input.lumisection" v-on:input="checkLumisectionJSON(step.input.lumisection)" :disabled="!editingInfo.steps">
                      <span v-if="lumisectionJSONValid" class="ml-2" style="color: #27ae60">Valid JSON</span>
                      <span v-else class="ml-2" style="color: #e74c3c">Invalid JSON</span>
                    </td>
                  </tr>
                </template>
                <template v-else>
                  <tr>
                    <td>--beamspot</td><td><input type="text" v-model="step.driver.beamspot" :disabled="!editingInfo.steps"></td>
                  </tr>
                  <tr>
                    <td>--conditions</td><td><input type="text" v-model="step.driver.conditions" :disabled="!editingInfo.steps"></td>
                  </tr>
                  <tr>
                    <td>--customise</td><td><input type="text" v-model="step.driver.customise" :disabled="!editingInfo.steps"></td>
                  </tr>
                  <tr>
                    <td>--customise_commands</td><td><input type="text" v-model="step.driver.customise_commands" :disabled="!editingInfo.steps"></td>
                  </tr>
                  <tr>
                    <td>--datatier</td><td><input type="text" v-model="step.driver.datatier" :disabled="!editingInfo.steps"></td>
                  </tr>
                  <tr>
                    <td>--era</td><td><input type="text" v-model="step.driver.era" :disabled="!editingInfo.steps"></td>
                  </tr>
                  <tr>
                    <td>--eventcontent</td><td><input type="text" v-model="step.driver.eventcontent" :disabled="!editingInfo.steps"></td>
                  </tr>
                  <tr>
                    <td>--filetype</td><td><input type="text" v-model="step.driver.filetype" :disabled="!editingInfo.steps"></td>
                  </tr>
                  <tr>
                    <td>--geometry</td><td><input type="text" v-model="step.driver.geometry" :disabled="!editingInfo.steps"></td>
                  </tr>
                  <tr>
                    <td>--hltProcess</td><td><input type="text" v-model="step.driver.hltProcess" :disabled="!editingInfo.steps"></td>
                  </tr>
                  <tr>
                    <td>--nStreams</td><td><input type="text" v-model="step.driver.nStreams" :disabled="!editingInfo.steps"></td>
                  </tr>
                  <tr>
                    <td>--pileup</td><td><input type="text" v-model="step.driver.pileup" :disabled="!editingInfo.steps"></td>
                  </tr>
                  <tr>
                    <td>--pileup_input</td><td><input type="text" v-model="step.driver.pileup_input" :disabled="!editingInfo.steps"></td>
                  </tr>
                  <tr>
                    <td>--process</td><td><input type="text" v-model="step.driver.process" :disabled="!editingInfo.steps"></td>
                  </tr>
                  <tr>
                    <td>--relval</td><td><input type="text" v-model="step.driver.relval" :disabled="!editingInfo.steps"></td>
                  </tr>
                  <tr>
                    <td>--runUnscheduled</td><td><input type="checkbox" v-model="step.driver.runUnscheduled" :disabled="!editingInfo.steps"></td>
                  </tr>
                  <tr>
                    <td>--scenario</td>
                    <td>
                      <select v-model="step.driver.scenario" :disabled="!editingInfo.steps">
                        <option></option>
                        <option>pp</option>
                        <option>cosmics</option>
                        <option>nocoll</option>
                        <option>HeavyIons</option>
                      </select>
                      {{step.scenario}}
                    </td>
                  </tr>
                  <tr>
                    <td>--step</td><td><input type="text" v-model="step.driver.step" :disabled="!editingInfo.steps"></td>
                  </tr>
                  <tr>
                    <td>Data, MC, FastSim</td>
                    <td>
                      <input type="radio"
                             class="mr-1"
                             v-model="step.driver.data"
                             :name="'step' + index + '_data_fast_mc'"
                             @click="step.driver.fast = false; step.driver.mc = false; step.driver.data = !step.driver.data" :value="true"
                             :disabled="!editingInfo.steps">--data
                      <input type="radio"
                             class="mr-1 ml-2"
                             v-model="step.driver.mc"
                             :name="'step' + index + '_data_fast_mc'"
                             @click="step.driver.data = false; step.driver.mc = !step.driver.mc" :value="true"
                             :disabled="!editingInfo.steps">--mc
                      <span v-if="!step.driver.data">
                        <input type="checkbox"
                              class="mr-1 ml-2"
                              v-model="step.driver.fast"
                              :disabled="!editingInfo.steps"/>--fast
                      </span>
                    </td>
                  </tr>
                  <tr>
                    <td>Extra</td><td><input type="text" v-model="step.driver.extra" placeholder="Any arguments that are not specified above" :disabled="!editingInfo.steps"></td>
                  </tr>
                  <tr>
                    <td>Fragment name</td><td><input type="text" v-model="step.driver.fragment_name" placeholder="E.g. Configuration/Generator/<filename>.py" :disabled="!editingInfo.steps"></td>
                  </tr>
                  <tr>
                    <td>GPU</td>
                    <td>
                      <select v-model="step.gpu.requires" :disabled="!editingInfo.steps">
                        <option>forbidden</option>
                        <option>optional</option>
                        <option>required</option>
                      </select>
                    </td>
                  </tr>
                  <tr v-if="step.gpu.requires != 'forbidden'">
                    <td>GPU Parameters</td>
                    <td>
                      <table>
                        <tr>
                          <td>GPU Memory</td>
                          <td><input type="number" v-model="step.gpu.gpu_memory" :disabled="!editingInfo.steps" min="0" max="32000" step="1000">MB</td>
                        </tr>
                        <tr>
                          <td>CUDA Capabilities</td>
                          <td><input type="text" v-model="step.gpu.cuda_capabilities" placeholder="E.g. 6.0,6.1,6.2" :disabled="!editingInfo.steps"></td>
                        </tr>
                        <tr>
                          <td>CUDA Runtime</td>
                          <td><input type="text" v-model="step.gpu.cuda_runtime" :disabled="!editingInfo.steps"></td>
                        </tr>
                        <tr>
                          <td>GPU Name</td>
                          <td><input type="text" v-model="step.gpu.gpu_name" :disabled="!editingInfo.steps"></td>
                        </tr>
                        <tr>
                          <td>CUDA Driver Version</td>
                          <td><input type="text" v-model="step.gpu.cuda_driver_version" :disabled="!editingInfo.steps"></td>
                        </tr>
                        <tr>
                          <td>CUDA Runtime Version</td>
                          <td><input type="text" v-model="step.gpu.cuda_runtime_version" :disabled="!editingInfo.steps"></td>
                        </tr>
                      </table>
                    </td>
                  </tr>
                </template>
              </table>
              <v-btn small class="mr-1 mb-1" color="error" @click="deleteStep(index)">Delete step {{index + 1}}</v-btn>
              <hr>
            </div>
            <v-btn small class="mr-1 mb-1 mt-1" color="primary" @click="addStep()">Add step {{listLength(editableObject.steps) + 1}}</v-btn>
          </td>
        </tr>
        <tr>
          <td>Time per event</td>
          <td><input type="number" v-model="editableObject.time_per_event" :disabled="!editingInfo.time_per_event">s</td>
        </tr>
        <tr>
          <td>Workflow ID</td>
          <td><input type="number" min="1" v-model="editableObject.workflow_id" :disabled="!editingInfo.workflow_id"></td>
        </tr>
        <tr>
          <td>Workflow Name</td>
          <td><input type="text" v-model="editableObject.workflow_name" :disabled="!editingInfo.workflow_name"></td>
        </tr>
      </table>
      <v-btn small class="mr-1 mt-1" color="primary" @click="save()">Save</v-btn>
      <v-btn small class="mr-1 mt-1" color="error" @click="cancel()">Cancel</v-btn>
    </v-card>
    <LoadingOverlay :visible="loading"/>
    <v-dialog v-model="errorDialog.visible"
              max-width="50%">
      <v-card>
        <v-card-title class="headline">
          {{errorDialog.title}}
        </v-card-title>
        <v-card-text>
          <span v-html="errorDialog.description"></span>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn small class="mr-1 mb-1" color="primary" @click="clearErrorDialog()">
            Dismiss
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script>
import axios from 'axios'
import { utilsMixin } from '../mixins/UtilsMixin.js'
import LoadingOverlay from './LoadingOverlay.vue'

export default {
  components: {
    LoadingOverlay
  },
  mixins: [
    utilsMixin
  ],
  data () {
    return {
      prepid: undefined,
      editableObject: {},
      editingInfo: {},
      loading: true,
      creatingNew: true,
      lumisectionJSONValid: true,
      errorDialog: {
        visible: false,
        title: '',
        description: '',
      }
    }
  },
  created () {
    let query = Object.assign({}, this.$route.query);
    if (query.prepid && query.prepid.length) {
      this.prepid = query.prepid;
    } else {
      this.prepid = '';
    }
    this.creatingNew = this.prepid.length == 0;
    this.loading = true;
    let component = this;
    let prepareStep = function(step) {
      step.step_type = step.input.dataset && step.input.dataset.length ? 'input' : 'driver';
      step.input.lumisection = JSON.stringify(step.input.lumisection);
      step.driver.datatier = step.driver.datatier.join(',');
      step.driver.eventcontent = step.driver.eventcontent.join(',');
      step.driver.step = step.driver.step.join(',');
    }
    axios.get('api/relvals/get_editable/' + this.prepid).then(response => {
      if (query.clone && query.clone.length) {
        axios.get('api/relvals/get_editable/' + query.clone).then(templateResponse => {
          templateResponse.data.response.object.prepid = response.data.response.object.prepid;
          templateResponse.data.response.object.history = response.data.response.object.history;
          templateResponse.data.response.object.status = response.data.response.object.status;
          templateResponse.data.response.object.workflows = response.data.response.object.workflows;
          templateResponse.data.response.object.output_datasets = response.data.response.object.output_datasets;
          for (let step of templateResponse.data.response.object.steps) {
            prepareStep(step);
          }
          component.editableObject = templateResponse.data.response.object;
          component.editingInfo = response.data.response.editing_info;
          component.loading = false;
        }).catch(error => {
          component.loading = false;
          component.showError('Error getting RelVal information', component.getError(error));
        });
      } else {
        for (let step of response.data.response.object.steps) {
          prepareStep(step);
        }
        component.editableObject = response.data.response.object;
        component.editingInfo = response.data.response.editing_info;
        component.loading = false;
      }
    }).catch(error => {
      component.loading = false;
      component.showError('Error getting RelVal information', component.getError(error));
    });
  },
  methods: {
    save: function() {
      let editableObject = this.makeCopy(this.editableObject);
      let component = this;
      editableObject.notes = editableObject.notes.trim();
      editableObject.fragment = editableObject.fragment.trim();
      for (let step of editableObject.steps) {
        step.input.lumisection = JSON.parse(step.input.lumisection);
        step.driver.datatier = this.cleanSplit(step.driver.datatier);
        step.driver.eventcontent = this.cleanSplit(step.driver.eventcontent);
        step.driver.step = this.cleanSplit(step.driver.step);
      }
      let httpRequest;
      this.loading = true;
      if (this.creatingNew) {
        httpRequest = axios.put('api/relvals/create', editableObject)
      } else {
        httpRequest = axios.post('api/relvals/update', editableObject)
      }
      httpRequest.then(response => {
        component.loading = false;
        window.location = 'relvals?prepid=' + response.data.response.prepid;
      }).catch(error => {
        component.loading = false;
        component.showError('Error saving RelVal', component.getError(error))
      });
    },
    cancel: function() {
      if (this.creatingNew) {
        window.location = 'relvals';
      } else {
        window.location = 'relvals?prepid=' + this.prepid;
      }
    },
    clearErrorDialog: function() {
      this.errorDialog.visible = false;
      this.errorDialog.title = '';
      this.errorDialog.description = '';
    },
    showError: function(title, description) {
      this.clearErrorDialog();
      this.errorDialog.title = title;
      this.errorDialog.description = description;
      this.errorDialog.visible = true;
    },
    addStep: function() {
      this.loading = true;
      let component = this;
      axios.get('api/relvals/get_default_step').then(response => {
        let steps = component.editableObject['steps'];
        let newStep = response.data.response;
        if (steps.length > 0) {
          let previousStep = steps[steps.length - 1];
          newStep['cmssw_release'] = previousStep['cmssw_release'];
          newStep['scram_arch'] = previousStep['scram_arch'];
          newStep.driver.conditions = previousStep.driver.conditions;
        }
        newStep.step_type = 'driver';
        newStep.input.lumisection = JSON.stringify(newStep.input.lumisection);
        newStep.driver.datatier = newStep.driver.datatier.join(',');
        newStep.driver.eventcontent = newStep.driver.eventcontent.join(',');
        newStep.driver.step = newStep.driver.step.join(',');
        steps.push(newStep);
        component.loading = false;
      }).catch(error => {
        component.loading = false;
        component.showError('Error getting step information', component.getError(error));
      });
    },
    deleteStep: function(index) {
      this.editableObject['steps'].splice(index, 1);
    },
    checkLumisectionJSON: function(jsonText) {
      try {
        JSON.parse(jsonText);
        this.lumisectionJSONValid = true;
      } catch(err) {
        this.lumisectionJSONValid = false;
      }
    },
  }
}
</script>
