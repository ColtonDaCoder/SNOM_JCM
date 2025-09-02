% This script file was generated using JCMcontrol.
% Please, open it with your local Matlab or Octave application.
addpath(fullfile(getenv('JCMROOT'), 'ThirdPartySupport', 'Matlab'));

%% register a new computer resource
jcmwave_daemon_shutdown();
jcmwave_daemon_add_workstation('Hostname', 'localhost', ...
			       'Multiplicity', 1, ...
			       'NThreads', 4);

%% define default key values
{% for param in params -%}
default_keys.{{'.'.join(param.name.split('/'))}} = {{param.value or '_{}_'.format(param.type)}};
{% endfor %}

%% Inspect results with default parameters
job_id = jcmwave_solve('{{project}}', default_keys);
[results, logs] = jcmwave_daemon_wait([job_id]);
result = results{1};
for ii=1:length(result)
   {% raw %}fprintf("=== Content of result{%d} ===",ii);{% endraw %}
   result{ii}
end 
jcmwave_view(result{1}.file);
 
{% block task %}{% endblock %}

%% shut down daemon
jcmwave_daemon_shutdown();