{% extends "BaseTemplate.m" %}

{% block task %}
%% Definition of the search domain
domain = {};
{% for param in params if param.type in ['real','complex','integer'] %}
domain({{loop.index}}).name = '{{param.name}}';
{% if param.type=='integer' -%}
domain({{loop.index}}).type = 'discrete';
domain({{loop.index}}).domain = [val1_,val2_,...];
{%- else -%}
domain({{loop.index}}).domain = [lower_,upper_];
{%- endif -%}
{%- endfor %}

%% Creation of the study object
study = jcmwave_optimizer_create_study('domain', domain, ...
                    'name','Optimization study', ...
                    'study_id', 'optimization1', ...
                    'save_dir', pwd);
study.set_parameters('max_iter', 100, 'num_parallel', 2);

%% Run a parallel minimization loop 
while(not(study.is_done))
    % Get new suggestion
    suggestion = study.get_suggestion();
    % Get keys vor simulation with default values filled in
    keys = default_keys;
    param_names = fieldnames(suggestion.sample);
    for ii = 1:length(param_names)
        param_name = param_names{ii};
        keys.(param_name) = suggestion.sample.(param_name);
    end
    % Start simulation job
    job_id = jcmwave_solve('{{project}}', keys, 'temporary', 'yes');
    study.open_jobs([job_id], suggestion);
    
    if(study.num_open_suggestions == study.num_parallel)        
        [suggestion_results, suggestion_id] = study.gather_results();
        result = suggestion_results{1};
        obs = Observation();
        % Please, define the objective here. This may be the output of 
        % a post process or a function of several ouput values. E.g.,
        % value = -1e32*real(result{2}.ElectricFieldEnergy{1}(1));        
        value = computed_value_;
        obs.add(value);
        study.add_observation(obs, suggestion_id);
    end
end

%% Inspect best parameters found during the study
keys = default_keys;
min_params = study.info.min_params;
param_names = fieldnames(min_params);
for ii = 1:length(param_names)
    param_name = param_names{ii};
    keys.(param_name) = suggestion.sample.(param_name);
end
job_id = jcmwave_solve('project.jcmp', keys);
[results, logs] = jcmwave_daemon_wait([job_id]);
jcmwave_view(results{1}{1}.file);

{% endblock %}