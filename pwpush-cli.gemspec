# coding: utf-8
lib = File.expand_path('../lib', __FILE__)
$LOAD_PATH.unshift(lib) unless $LOAD_PATH.include?(lib)
require 'pwpush/cli/version'

Gem::Specification.new do |spec|
  spec.name          = "pwpush-cli"
  spec.version       = Pwpush::Cli::VERSION
  spec.authors       = ["Peter Giacomo Lombardo"]
  spec.email         = ["pglombardo@gmail.com"]

  spec.summary       = %q{Eventual command line interface to PasswordPusher}
  spec.description   = %q{This gem provides a command line utility to push passwords on the fly to https://pwpush.com}
  spec.homepage      = "https://pwpush.com"
  spec.license       = "MIT"

  # Prevent pushing this gem to RubyGems.org by setting 'allowed_push_host', or
  # delete this section to allow pushing this gem to any host.
  if spec.respond_to?(:metadata)
    spec.metadata['allowed_push_host'] = "TODO: Set to 'http://mygemserver.com'"
  else
    raise "RubyGems 2.0 or newer is required to protect against public gem pushes."
  end

  spec.files         = `git ls-files -z`.split("\x0").reject { |f| f.match(%r{^(test|spec|features)/}) }
  spec.bindir        = "exe"
  spec.executables   = spec.files.grep(%r{^exe/}) { |f| File.basename(f) }
  spec.require_paths = ["lib"]

  spec.add_development_dependency "bundler", "~> 1.10"
  spec.add_development_dependency "rake", "~> 10.0"
  spec.add_development_dependency "minitest"
end
