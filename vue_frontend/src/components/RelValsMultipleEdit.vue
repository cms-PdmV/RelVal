<template>
  <div>
    <h1 class="page-title"><span class="font-weight-light">Editing</span> {{prepids.length}} <span class="font-weight-light">RelVals</span></h1>
    <v-card raised class="page-card">
      <h2>List of RelVals</h2>
      <ul>
        <li v-for="prepid in prepids" :key="prepid"><a :href="'relvals?prepid=' + prepid" title="Open RelVal in new tab" target="_blank">{{prepid}}</a></li>
      </ul>
      <h2>Values to be updated in {{prepids.length}} RelVals</h2>
      <table v-if="editableObjects">
        <tr>
          <td>CPU Cores (-t)</td>
          <td><input type="number" v-model="fakeEditableObject.cpu_cores" min="1" max="8"></td>
        </tr>
        <tr>
          <td>Label (--label)</td>
          <td><input type="text" v-model="fakeEditableObject.label" placeholder="E.g. gcc8 or rsb or pmx"></td>
        </tr>
        <tr>
          <td>Memory</td>
          <td><input type="number" v-model="fakeEditableObject.memory" min="0" max="32000" step="1000">MB</td>
        </tr>
        <tr>
          <td>Notes</td>
          <td><textarea v-model="fakeEditableObject.notes" placeholder="E.g. Goals, comments, links to TWiki and HN"></textarea></td>
        </tr>
        <tr>
          <td>Sample Tag</td>
          <td><input type="text" v-model="fakeEditableObject.sample_tag" placeholder="E.g. Run2, Run3, Phase2, HIN, GEN, ..."></td>
        </tr>

        <tr v-if="fakeEditableObject.steps">
          <td>Steps ({{listLength(fakeEditableObject.steps)}})</td>
          <td>
            <div v-for="(step, index) in fakeEditableObject.steps" :key="index">
              <h3>Step {{index + 1}}</h3>
              <table>
                <tr>
                  <td>Name</td><td><input type="text" v-model="step.name"></td>
                </tr>
                <tr>
                  <td>CMSSW Release</td><td><input type="text" v-model="step.cmssw_release"></td>
                </tr>
                <tr v-if="index == 0 && step.step_type != 'input'">
                  <td>Events per lumi</td><td><input type="text" v-model="step.events_per_lumi"></td>
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
                    <td>
                      <input type="text" style="width: 75%;font-family: monospace;" v-model="step.input.lumisection" v-on:input="checkLumisectionJSON(step.input.lumisection)">
                      <span v-if="lumisectionJSONValid" class="ml-2" style="color: #27ae60">Valid JSON</span>
                      <span v-else class="ml-2" style="color: #e74c3c">Invalid JSON</span>
                    </td>
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
                            @click="setValue(step.driver, 'data', !Boolean(step.driver.data));
                                    setValue(step.driver, 'mc', false);
                                    setValue(step.driver, 'fast', false);"
                          >--data
                    <input type="radio"
                            class="mr-1 ml-2"
                            :checked="step.driver['mc']"
                            :name="'step' + index + '_data_fast_mc'"
                            @click="setValue(step.driver, 'data', false);
                                    setValue(step.driver, 'mc', !Boolean(step.driver.mc));
                                    deleteAttribute(step.driver, 'fast');"
                          >--mc
                    <span v-if="!Boolean(step.driver.data)">
                      <input type="checkbox"
                            class="mr-1 ml-2"
                            :checked="step.driver['fast']"
                            @click="setValue(step.driver, 'fast', !Boolean(step.driver.fast));"
                            />--fast
                    </span>
                  </td>
                </tr>
                <tr>
                  <td>Extra</td><td><input type="text" v-model="step.driver.extra" placeholder="Any arguments that are not specified above"></td>
                </tr>
              </table>
              <hr>
            </div>
          </td>
        </tr>

        <tr>
          <td>Time per event</td>
          <td><input type="number" v-model="fakeEditableObject.time_per_event">s</td>
        </tr>

      </table>
      <!-- <pre>{{JSON.stringify(fakeEditableObject, undefined, 2)}}</pre> -->
      <h2>List of edits that will be done</h2>
      <ul>
        <div v-for="(value, key) in fakeEditableObject" :key="key">
          <template v-if="key != 'steps'">
            <li>
              <b>{{key}}</b> will be set to <b>{{value}}</b> 
              <v-btn small class="ml-1 mb-1" style="height: 22px" color="error" @click="deleteAttribute(fakeEditableObject, key)">Remove</v-btn>
            </li>
          </template>
        </div>
        <div v-for="(step, index) in fakeEditableObject.steps" :key="index">
          <li v-if="Object.keys(step).length > 2 || Object.keys(step.input).length || Object.keys(step.driver).length">
            Step {{index + 1}}:
            <ul>
              <div v-for="(value, key) in step" :key="key">
                <template v-if="key != 'driver' && key != 'input'">
                  <li>
                    <b>{{key}}</b> in <b>Step {{index + 1}}</b> will be set to <b>{{niceBoolean(value)}}</b>
                    <v-btn small class="ml-1 mb-1" style="height: 22px" color="error" @click="deleteAttribute(step, key)">Remove</v-btn>
                  </li>
                </template>
              </div>
              <template v-if="index == 0">
                <div v-for="(value, key) in step.input" :key="key">
                  <li>
                    <b>{{key}}</b> in <b>Step {{index + 1}}</b> will be set to <b>{{niceBoolean(value)}}</b>
                    <v-btn small class="ml-1 mb-1" style="height: 22px" color="error" @click="deleteAttribute(step.input, key)">Remove</v-btn>
                  </li>
                </div>
              </template>
              <div v-for="(value, key) in step.driver" :key="key">
                <li>
                  <b>{{key}}</b> in <b>Step {{index + 1}}</b> will be set to <b>{{niceBoolean(value)}}</b>
                  <v-btn small class="ml-1 mb-1" style="height: 22px" color="error" @click="deleteAttribute(step.driver, key)">Remove</v-btn>
                </li>
              </div>
            </ul>
          </li>
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
import Vue from 'vue'
import axios from 'axios'
import { utilsMixin } from '../mixins/UtilsMixin.js'
import LoadingOverlay from './LoadingOverlay.vue'

export default {
  components: {
    LoadingOverlay,
  },
  mixins: [
    utilsMixin
  ],
  data () {
    return {
      prepids: [],
      editableObjects: [],
      fakeEditableObject: {},
      loading: true,
      lumisectionJSONValid: true,
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
      let relvals = response.data.response.object;
      if (component.prepids.length == 1) {
        relvals = [relvals];
      }
      let maxSteps = 0;
      for (let relval of relvals) {
        maxSteps = Math.max(maxSteps, relval.steps.length);
      }
      let steps = [];
      for (let i = 0; i < maxSteps; i++) {
        steps.push({'input': {}, 'driver': {}});
      }
      this.$set(this.fakeEditableObject, 'steps', steps);
      component.editableObjects = response.data.response.object;
      component.loading = false;
    }).catch(error => {
      component.loading = false;
      component.showError('Error getting RelVal information', component.getError(error));
    });
  },
  methods: {
    save: function() {
      let editableObjects = this.makeCopy(this.editableObjects);
      let component = this;
      // First - update RelVal attributes
      for (let key in this.fakeEditableObject) {
        if (key == 'steps') {
          continue;
        }
        const value = this.fakeEditableObject[key];
        for (let relval of editableObjects) {
          relval[key] = value;
        }
      }
      // Then - update RelVal steps attributes
      for (let stepIndex in this.fakeEditableObject.steps) {
        const step = this.fakeEditableObject.steps[stepIndex];
        for (let relval of editableObjects) {
          const relvalSteps = relval.steps;
          if (stepIndex >= relvalSteps.length) {
            continue;
          }
          let relvalStep = relvalSteps[stepIndex];
          // Main RelVal step attributes
          for (let key in step) {
            relvalStep[key] = step[key];
          }
          // RelVal step input attributes
          for (let key in step.input) {
            if (key == 'lumisection') {
              relvalStep.input[key] = JSON.parse(step.input[key]);
            } else {
              relvalStep.input[key] = step.input[key];
            }
          }
          // RelVal driver attributes
          for (let key in step.driver) {
            if (key == 'datatier' || key == 'eventcontent' || key == 'step') {
              relvalStep.driver[key] = this.cleanSplit(step.driver[key]);
            } else {
              relvalStep.driver[key] = step.driver[key];
            }
          }
        }
      }

      this.loading = true;
      let httpRequest = axios.post('api/relvals/update', editableObjects)
      httpRequest.then(response => {
        component.loading = false;
        window.location = 'relvals?prepid=' + this.prepids.join(',');
      }).catch(error => {
        component.loading = false;
        component.showError('Error saving RelVal', component.getError(error))
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
    },
    niceBoolean: function(b) {
      // Convert boolean to Yes or No or return original value
      return b === false ? 'No' : b === true ? 'Yes' : b;
    },
    setValue: function(obj, key, value) {
      this.$set(obj, key, value);
    },
    deleteAttribute: function(obj, name) {
      obj[name] = undefined;
      delete obj[name];
    }
  }
}
</script>

<style scoped>
h2 {
  text-align: center;
}
</style>