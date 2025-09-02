{% extends "BaseTemplate.m" %}

{% block task %}
%% create resultbag. Results will be stored in file ./resultbag.mat
resultbag = jcmwave_resultbag('resultbag.mat');

%% define set of keys for a multi-dimensional parameter scan
{% for param in params if param.type in ['real','complex','integer'] %}
{% if loop.index > 2 -%}%{%- endif -%}
range.{{param.name}} = lower_:steps_size_:upper_;
{%- endfor %}

% Define 2D scan grid. This expression works similarly also for
% higher-dimensional scans
[ 
{%- for param in params if param.type in ['real','complex','integer'] -%}
{%- if loop.index <= 2 -%}
scan.{{param.name}}{{ "," if loop.index<2 and not loop.last }}
{%- endif -%}
{%- endfor -%}
] = ndgrid(
{%- for param in params if param.type in ['real','complex','integer'] -%}
{%- if loop.index <= 2 -%}
range.{{param.name}}{{ "," if loop.index<2 and not loop.last}}
{%- endif -%}
{%- endfor -%}    
);
 
% fill a set of keys with scan values
scan_names = fieldnames(scan); 
keyset = repmat(default_keys, size(scan.(scan_names{1}))); 
for ii = 1 : numel(keyset)
  for jj = 1 : numel(scan_names)
     param_name = scan_names{jj};
     keyset(ii).(param_name) = scan.(param_name)(ii);
  end
end

%% run the parameter scan
job_ids = [];
for ii = 1 : numel(keyset)
   keys = keyset(ii);
   job_ids(end+1) = jcmwave_solve('{{project}}', keys, resultbag, 'temporary', 'yes');
end

% jcm_deamon_wait adds all results to the resultbag
jcmwave_daemon_wait(job_ids, resultbag);

%% plot results
data = zeros(
{%- for param in params if param.type in ['real','complex','integer'] -%}
{%- if loop.index <= 2 -%}
length(range.{{param.name}}){{ "," if loop.index<2 and not loop.last}}{{ ",1" if loop.index<2 and loop.last}}
{%- endif -%}
{%- endfor -%}    
);
for ii = 1 : numel(keyset)
   keys = keyset(ii);
   result = resultbag.get_result(keys);
   % Please, define the objective here. This may be the output of 
   % a post process or a function of several ouput values. E.g.,
   % data(ii) = 1e32*real(result{2}.ElectricFieldEnergy{1}(1));
   data(ii) = computed_value_;
end

if size(data,2) == 1
  {% for param in params if param.type in ['real','integer'] -%}
  {%- if loop.index <= 1 -%}
  plot(scan.{{param.name}},data,'+-');
  xlabel('{{param.name}}');
  {%- endif -%}
  {%- endfor %}    
else
  surf(
{%- for param in params if param.type in ['real','integer'] -%}
{%- if loop.index <= 2 -%}
scan.{{param.name}},
{%- endif -%}
{%- endfor -%}    
data);
  colorbar;
  {% for param in params if param.type in ['real','integer'] -%}
  {% if loop.index == 1 -%}
  xlabel('{{param.name}}');
  {% elif loop.index == 2 -%}
  ylabel('{{param.name}}');
  {%- endif -%}
  {%- endfor %}    
end

{% endblock %}
