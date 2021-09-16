<template>
  <div>
    <h1 class="page-title"><span class="font-weight-light">Editing</span> {{prepids.length}} <span class="font-weight-light">RelVals</span></h1>
    <v-card raised class="page-card">
      <h2>List of RelVals</h2>
      <ul>
        <li v-for="prepid in prepids" :key="prepid"><a :href="'relvals?prepid=' + prepid" title="Open RelVal in new tab" target="_blank">{{prepid}}</a></li>
      </ul>
      <h2>Values to be updated in {{prepids.length}} RelVals</h2>
      <table v-if="editingObject">
        <tr>
          <td>CPU Cores (-t)</td>
          <td><input type="number" v-model="editingObject.cpu_cores" min="1" max="8"></td>
        </tr>
        <tr>
          <td>Label (--label)</td>
          <td><input type="text" v-model="editingObject.label" placeholder="E.g. gcc8 or rsb or pmx"></td>
        </tr>
        <tr>
          <td>Memory</td>
          <td><input type="number" v-model="editingObject.memory" min="0" max="32000" step="1000">MB</td>
        </tr>
        <tr>
          <td>Notes</td>
          <td><textarea v-model="editingObject.notes" placeholder="E.g. Goals, comments, links to TWiki and HN"></textarea></td>
        </tr>
        <tr>
          <td>Sample Tag</td>
          <td><input type="text" v-model="editingObject.sample_tag" placeholder="E.g. Run2, Run3, Phase2, HIN, GEN, ..."></td>
        </tr>
        <tr>
          <td>Size per event</td>
          <td><input type="number" v-model="editingObject.size_per_event">kB</td>
        </tr>
        <tr v-if="editingObject.steps">
          <td>Steps ({{listLength(editingObject.steps)}})</td>
          <td>
            <div v-for="(step, index) in editingObject.steps" :key="index">
              <h3>Step {{index + 1}}</h3>
              <table v-if="!step.deleted">
                <tr>
                  <td>Name</td><td><input type="text" v-model="step.name"></td>
                </tr>
                <tr>
                  <td>CMSSW Release</td><td><input type="text" v-model="step.cmssw_release"></td>
                </tr>
                <tr>
                  <td>SCRAM Arch</td><td><input type="text" v-model="step.scram_arch" placeholder="If empty, uses default value of the release"></td>
                </tr>
                <tr v-if="index == 0 && step.step_type != 'input'">
                  <td>Events per lumi</td><td><input type="text" v-model="step.events_per_lumi"></td>
                </tr>
                <tr v-if="step.step_type != 'input'">
                  <td>Keep output</td><td><input type="checkbox" v-model="step.keep_output"></td>
                </tr>
                <tr v-if="index != 0">
                  <td>Lumis per job</td><td><input type="text" v-model="step.lumis_per_job"></td>
                </tr>
                <template v-if="index == 0">
                  <tr>
                    <td>Dataset</td><td><input type="text" v-model="step.input.dataset"></td>
                  </tr>
                  <tr>
                    <td>Label</td><td><input type="text" v-model="step.input.label"></td>
                  </tr>
                  <tr>
                    <td>Lumisection ranges</td>
                    <td><JSONField v-model="step.input.lumisection"/></td>
                  </tr>
                </template>
                <tr>
                  <td>--beamspot</td><td><input type="text" v-model="step.driver.beamspot"></td>
                </tr>
                <tr>
                  <td>--conditions</td><td><input type="text" v-model="step.driver.conditions"></td>
                </tr>
                <tr>
                  <td>--customise</td><td><input type="text" v-model="step.driver.customise"></td>
                </tr>
                <tr>
                  <td>--customise_commands</td><td><input type="text" v-model="step.driver.customise_commands"></td>
                </tr>
                <tr>
                  <td>--datatier</td><td><input type="text" v-model="step.driver.datatier"></td>
                </tr>
                <tr>
                  <td>--era</td><td><input type="text" v-model="step.driver.era"></td>
                </tr>
                <tr>
                  <td>--eventcontent</td><td><input type="text" v-model="step.driver.eventcontent"></td>
                </tr>
                <tr>
                  <td>--filetype</td><td><input type="text" v-model="step.driver.filetype"></td>
                </tr>
                <tr>
                  <td>--geometry</td><td><input type="text" v-model="step.driver.geometry"></td>
                </tr>
                <tr>
                  <td>--hltProcess</td><td><input type="text" v-model="step.driver.hltProcess"></td>
                </tr>
                <tr>
                  <td>--nStreams</td><td><input type="text" v-model="step.driver.nStreams"></td>
                </tr>
                <tr>
                  <td>--pileup</td><td><input type="text" v-model="step.driver.pileup"></td>
                </tr>
                <tr>
                  <td>--pileup_input</td><td><input type="text" v-model="step.driver.pileup_input"></td>
                </tr>
                <tr>
                  <td>--process</td><td><input type="text" v-model="step.driver.process"></td>
                </tr>
                <tr>
                  <td>--relval</td><td><input type="text" v-model="step.driver.relval"></td>
                </tr>
                <tr>
                  <td>--runUnscheduled</td><td><input type="checkbox" v-model="step.driver.runUnscheduled"></td>
                </tr>
                <tr>
                  <td>--scenario</td>
                  <td>
                    <select v-model="step.driver.scenario">
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
                  <td>--step</td><td><input type="text" v-model="step.driver.step"></td>
                </tr>
                <tr>
                  <td>Data, MC, FastSim</td>
                  <td>
                    <input type="radio"
                            class="mr-1"
                            :checked="step.driver['data']"
                            :name="'step' + index + '_data_fast_mc'"
                            @click="step.driver.data = !Boolean(step.driver.data);
                                    step.driver.mc =  false;
                                    step.driver.fast = false;"
                          >--data
                    <input type="radio"
                            class="mr-1 ml-2"
                            :checked="step.driver['mc']"
                            :name="'step' + index + '_data_fast_mc'"
                            @click="step.driver.data = false;
                                    step.driver.mc = !Boolean(step.driver.mc);
                                    step.driver.fast = false;"
                          >--mc
                    <span v-if="!Boolean(step.driver.data)">
                      <input type="checkbox"
                            class="mr-1 ml-2"
                            :checked="step.driver['fast']"
                            @click="step.driver.fast = !Boolean(step.driver.fast);"
                            />--fast
                    </span>
                  </td>
                </tr>
                <tr>
                  <td>Extra</td><td><input type="text" v-model="step.driver.extra" placeholder="Any arguments that are not specified above"></td>
                </tr>

                <tr>
                  <td>GPU</td>
                  <td>
                    <select v-model="step.gpu.requires">
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
                        <td><input type="number" v-model="step.gpu.gpu_memory" min="0" max="32000" step="1000">MB</td>
                      </tr>
                      <tr>
                        <td>CUDA Capabilities</td>
                        <td><input type="text" v-model="step.gpu.cuda_capabilities" placeholder="E.g. 6.0,6.1,6.2"></td>
                      </tr>
                      <tr>
                        <td>CUDA Runtime</td>
                        <td><input type="text" v-model="step.gpu.cuda_runtime"></td>
                      </tr>
                      <tr>
                        <td>GPU Name</td>
                        <td><input type="text" v-model="step.gpu.gpu_name"></td>
                      </tr>
                      <tr>
                        <td>CUDA Driver Version</td>
                        <td><input type="text" v-model="step.gpu.cuda_driver_version"></td>
                      </tr>
                      <tr>
                        <td>CUDA Runtime Version</td>
                        <td><input type="text" v-model="step.gpu.cuda_runtime_version"></td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>
              <v-btn v-if="!step.deleted" small class="mr-1 mb-1" color="error" @click="deleteStep(index)">Delete step {{index + 1}}</v-btn>
              <span v-if="step.deleted">
                Deleted
              </span>
              <hr>
            </div>
          </td>
        </tr>
        <tr>
          <td>Time per event</td>
          <td><input type="number" v-model="editingObject.time_per_event">s</td>
        </tr>
        <tr>
          <td>Workflow Name</td>
          <td><input type="text" v-model="editingObject.workflow_name"></td>
        </tr>
      </table>
      <!-- <pre style="font-size: 0.6em">{{JSON.stringify(editingObject, undefined, 2)}}</pre> -->
      <h2>List of edits that will be done</h2>
      <ul>
        <div v-for="(value, key) in differences" :key="key">
          <template v-if="key != 'steps'">
            <li>
              <b>{{key}}</b> will be set to <b>{{value}}</b> 
              <v-btn small
                     class="ml-1 mb-1"
                     color="error"
                     @click="editingObject[key] = originalEditingObject[key]">Remove edit</v-btn>
            </li>
          </template>
          <template v-if="key == 'steps'">
            <div v-for="(step, index) in value" :key="index">
              <template v-if="!step.deleted">
                <div v-for="(stepValue, stepKey) in step" :key="stepKey">
                  <template v-if="['driver', 'input', 'gpu'].includes(stepKey)">
                    <li v-for="(driverValue, driverKey) in stepValue" :key="driverKey">
                      <b>{{driverKey}}</b> in <b>Step {{index + 1}}</b> will be set to <b>{{driverValue}}</b>
                      <v-btn small
                             class="ml-1 mb-1"
                             color="error"
                             @click="editingObject.steps[index][stepKey][driverKey] = originalEditingObject.steps[index][stepKey][driverKey]">Remove edit</v-btn>
                    </li>
                  </template>
                  <template v-if="!['deleted', 'driver', 'input', 'gpu'].includes(stepKey)">
                    <li>
                      <b>{{stepKey}}</b> in <b>Step {{index + 1}}</b> will be set to <b>{{stepValue}}</b>
                      <v-btn small
                             class="ml-1 mb-1"
                             color="error"
                             @click="editingObject.steps[index][stepKey] = originalEditingObject.steps[index][stepKey]">Remove edit</v-btn>
                    </li>
                  </template>
                </div>
              </template>
              <li v-if="step.deleted">
                Step {{index + 1}} will be <b>deleted in all {{prepids.length}}</b> RelVals
                <v-btn small class="ml-1 mb-1" color="error" @click="editingObject.steps[index].deleted = false">Remove edit</v-btn>
              </li>
            </div>
          </template>
        </div>
      </ul>
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
import JSONField from './JSONField.vue'

export default {
  components: {
    LoadingOverlay,
    JSONField
  },
  mixins: [
    utilsMixin
  ],
  data () {
    return {
      prepids: [],
      objects: [],
      editingObject: undefined,
      originalEditingObject: {},
      differences: {},
      loading: true,
      errorDialog: {
        visible: false,
        title: '',
        description: '',
      }
    }
  },
  created () {
    this.loading = true;
    let query = Object.assign({}, this.$route.query);
    this.prepids = this.cleanSplit(query['prepid']);
    let component = this;
    axios.get('api/relvals/get_editable/' + this.prepids.join(',')).then(response => {
      let objects = response.data.response.object;
      if (component.prepids.length == 1) {
        objects = [objects];
      }
      for (let obj of objects) {
        this.prepareObjectForEditing(obj);
      }
      component.objects = objects;
      let editingObject = component.makeEditingObject(objects);
      component.$set(component, 'editingObject', component.makeCopy(editingObject));
      component.$set(component, 'originalEditingObject', component.makeCopy(editingObject))
      component.loading = false;
    }).catch(error => {
      component.loading = false;
      component.showError('Error getting RelVal information', component.getError(error));
    });
  },
  watch: {
    editingObject: {
      deep: true,
      handler() {
        let differences = {};
        let ref = this.originalEditingObject;
        let tar = this.editingObject;
        for (let key of Object.keys(ref)) {
          if (key == 'steps') {
            continue
          }
          if (ref[key] != tar[key]) {
            differences[key] = tar[key]
          }
        }
        // Steps diffs
        let stepsDiffs = [];
        for (let i = 0; i < ref.steps.length; i++) {
          let refStep = ref.steps[i];
          let tarStep = tar.steps[i];
          let stepDiff = {'deleted': tarStep.deleted, 'driver': {}, 'input': {}, 'gpu': {}};
          stepsDiffs.push(stepDiff);
          for (let key of Object.keys(refStep)) {
            if (['driver', 'input', 'gpu'].includes(key)) {
              for (let driverKey of Object.keys(refStep[key])) {
                if (refStep[key][driverKey] != tarStep[key][driverKey]) {
                  stepDiff[key][driverKey] = tarStep[key][driverKey];
                }
              }
            } else if (refStep[key] != tarStep[key]) {
              stepDiff[key] = tarStep[key];
            }
          }
        }
        if (stepsDiffs.some(s => s.deleted || Object.keys(s).length > 1)) {
          differences['steps'] = stepsDiffs;
        }
        this.$set(this, 'differences', differences);
      }
    }
  },
  methods: {
    prepareObjectForEditing: function(obj) {
      for (let step of obj.steps) {
        step.input.lumisection = this.stringifyLumis(step.input.lumisection);
        step.driver.datatier = step.driver.datatier.join(',');
        step.driver.eventcontent = step.driver.eventcontent.join(',');
        step.driver.step = step.driver.step.join(',');
        step.gpu.cuda_capabilities = step.gpu.cuda_capabilities.join(',');
      }
    },
    prepareObjectForSaving: function(obj) {
      obj.notes = obj.notes.trim();
      for (let step of obj.steps) {
        step.input.lumisection = step.input.lumisection ? JSON.parse(step.input.lumisection) : {};
        step.driver.datatier = this.cleanSplit(step.driver.datatier);
        step.driver.eventcontent = this.cleanSplit(step.driver.eventcontent);
        step.driver.step = this.cleanSplit(step.driver.step);
        step.gpu.cuda_capabilities = this.cleanSplit(step.gpu.cuda_capabilities);
      }
    },
    jsonDiff: function(obj1, obj2) {
      return JSON.stringify(obj1) != JSON.stringify(obj2);
    },
    getCommonValue: function(objects, callback) {
      for (let i = 0; i < objects.length - 1; i++) {
        if (this.jsonDiff(callback(objects[i]), callback(objects[i + 1]))) {
          return null;
        }
      }
      return callback(objects[0]);
    },
    makeEditingObject: function(relvals) {
      let editingObject = {};
      // Primitive attributes
      for (let key of ['cpu_cores', 'label', 'memory', 'notes', 'sample_tag', 'size_per_event', 'time_per_event', 'workflow_name']) {
        editingObject[key] = this.getCommonValue(relvals, (r) => r[key]);
      }
      // Steps
      editingObject.steps = Array(Math.min(...relvals.map(x => x.steps.length)));
      for (let i = 0; i < editingObject.steps.length; i++) {
        editingObject.steps[i] = {'deleted': false, 'driver': {}, 'input': {}, 'gpu': {}};
      }
      // Step attributes
      for (let key of Object.keys(relvals[0].steps[0])) {
        if (['driver', 'input', 'gpu'].includes(key)) {
          for (let i = 0; i < editingObject.steps.length; i++) {
            for (let driverKey of Object.keys(relvals[0].steps[i][key])) {
              editingObject.steps[i][key][driverKey] = this.getCommonValue(relvals, (r) => r.steps[i][key][driverKey]);
            }
          }
        } else {
          for (let i = 0; i < editingObject.steps.length; i++) {
            editingObject.steps[i][key] = this.getCommonValue(relvals, (r) => r.steps[i][key]);
          }
        }
      }
      return editingObject;
    },
    save: function() {
      let objects = this.makeCopy(this.objects);
      let component = this;
      for (let obj of objects) {
        for (let key of Object.keys(this.differences)) {
          let difference = this.differences[key];
          if (key == 'steps') {
            for (let stepIndex = 0; stepIndex < difference.length; stepIndex++) {
              let diffStep = difference[stepIndex];
              if (diffStep.deleted) {
                obj.steps[stepIndex] = undefined;
              } else {
                let objStep = obj.steps[stepIndex];
                for (let stepKey of Object.keys(diffStep)) {
                  if (['driver', 'input', 'gpu'].includes(stepKey)) {
                    for (let driverKey of Object.keys(diffStep[stepKey])) {
                      objStep[stepKey][driverKey] = diffStep[stepKey][driverKey];
                    }
                  } else if (stepKey != 'deleted') {
                    objStep[stepKey] = diffStep[stepKey];
                  }
                }
              }
            }
            obj.steps = obj.steps.filter(s => s !== undefined);
          } else {
            obj[key] = difference;
          }
        }
        this.prepareObjectForSaving(obj);
      }
      this.loading = true;
      let httpRequest = axios.post('api/relvals/update', objects)
      httpRequest.then(response => {
        component.loading = false;
        window.location = 'relvals?prepid=' + response.data.response.map(x => x.prepid).join(',');
      }).catch(error => {
        component.loading = false;
        component.showError('Error saving relvals', component.getError(error))
      });
    },
    cancel: function() {
      window.location = 'relvals?prepid=' + this.prepids.join(',');
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
    }
  }
}
</script>

<style scoped>
h2 {
  text-align: center;
}
</style>
