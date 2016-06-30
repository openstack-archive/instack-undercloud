source 'https://rubygems.org'

group :development, :test do
  gem 'puppetlabs_spec_helper', :require => false

  # FIXME: need to install puppet-lint gem from github.com because of
  # https://github.com/rodjek/puppet-lint/issues/409
  # We pin to the last commit before the release of v2.0.0, because
  # puppet-lint_variable_contains_upcase depends on puppet-lint v1.x.
  gem 'puppet-lint', :git => 'git://github.com/rodjek/puppet-lint.git', :ref => 'b04a35f'
  gem 'puppet-lint-absolute_classname-check'
  gem 'puppet-lint-absolute_template_path'
  gem 'puppet-lint-trailing_newline-check'

  # Puppet 4.x related lint checks
  gem 'puppet-lint-unquoted_string-check'
  gem 'puppet-lint-leading_zero-check'
  gem 'puppet-lint-variable_contains_upcase'
  gem 'puppet-lint-numericvariable'
end

if puppetversion = ENV['PUPPET_GEM_VERSION']
  gem 'puppet', puppetversion, :require => false
else
  gem 'puppet', :require => false
end

# vim:ft=ruby
