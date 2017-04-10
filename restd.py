#!/usr/bin/env python
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import tornado.autoreload
from tornado.options import options
import tornado.web
from tornado.ioloop import IOLoop
from tornado.log import app_log
import tornado.http1connection

from opsrest.settings import settings
from opsrest.application import OvsdbApiApplication
from opsrest.manager import OvsdbConnectionManager
import ops.dc

import ovs.unixctl
import ovs.unixctl.server
import ops_diagdump
import ovs.vlog
import argparse
import subprocess
import sys
import os
from tempfile import mkstemp


vlog=ovs.vlog.Vlog('restd')
# enable logging
from tornado.log import enable_pretty_logging
options.logging = settings['logging']
enable_pretty_logging()

SSL_PRIV_DIR = "/etc/ssl/private"
SSL_PRIV_KEY_FILE = "/etc/ssl/private/server-private.key"
SSL_CRT_FILE = "/etc/ssl/certs/server.crt"


def create_ssl_pki():
    if not os.path.exists(SSL_PRIV_DIR):
        os.mkdir(SSL_PRIV_DIR, 0700)

    if os.path.isfile(SSL_CRT_FILE) and os.path.isfile(SSL_PRIV_KEY_FILE):
        # Create these files only once on system bootup.
        app_log.debug("SSL default key/cert already exists")
        return;

    app_log.info("Creating default SSL key pair")
    subprocess.call(['openssl', 'genrsa', '-out', SSL_PRIV_KEY_FILE,
                     '2048'])

    fd, ssl_csr_file = mkstemp()
    subprocess.call(['openssl', 'req', '-new', '-key',
                     SSL_PRIV_KEY_FILE, '-out',
                     ssl_csr_file, '-subj',
                     '/C=US/ST=California/L=Palo Alto/O=HPE'])

    subprocess.call(['openssl', 'x509', '-req', '-days', '14600', '-in',
                     ssl_csr_file, '-signkey',
                     SSL_PRIV_KEY_FILE, '-out',
                     SSL_CRT_FILE])
    os.close(fd)
    os.unlink(ssl_csr_file)


def diag_basic_handler(argv):
    # argv[0] is set to the string "basic"
    # argv[1] is set to the feature name, e.g. rest
    feature = argv.pop()
    buff = "Diagnostic dump response for feature " + feature + ".\n"
    buff += "Active HTTPS connections:\n"
    for conn in HTTPS_server._connections:
        buff += "  Client IP is %s\n" % conn.context
    buff += "Transactions list:\n"
    buff += "  Index\t  Status\n"
    buff += "  ---------------\n"
    transactions = app.manager.transactions
    for index, txn in enumerate(transactions.txn_list):
        buff += "  %s\t  %s\n" % (index, txn.status)
    buff += "Total number of pending "\
            "transactions is %s" % len(transactions.txn_list)
    return buff


class UnixctlManager:
    def start(self):
        app_log.info("Creating unixctl server")
        ovs.daemon.set_pidfile(None)
        ovs.daemon._make_pidfile()
        global unixctl_server
        error, unixctl_server = ovs.unixctl.server.UnixctlServer.create(None)
        if error:
            app_log.error("Failed to create unixctl server")
        else:
            app_log.info("Created unixctl server")
            app_log.info("Init diag dump")
            ops_diagdump.init_diag_dump_basic(diag_basic_handler)
            # Add handler in tornado
            IOLoop.current().add_handler(
                unixctl_server._listener.socket.fileno(),
                self.unixctl_run,
                IOLoop.READ | IOLoop.ERROR)

    def unixctl_run(self, fd=None, events=None):
        app_log.debug("Inside unixctl_run")
        if events & IOLoop.ERROR:
            app_log.error("Unixctl socket fd %s error" % fd)
        elif events & IOLoop.READ:
            app_log.debug("READ on unixctl")
            unixctl_server.run()


def main():
    global app, HTTPS_server, HTTP_server

    # TODO: Using two arg parsers is a mess. Right now users are required
    # to do "restd --help" for tornado options and "rest -- --help" for
    # restd options. This should be changed to use either tornado's options
    # *or* argparser (or equiv.).
    sys.argv = [sys.argv[0], ] + options.parse_command_line()
    options.parse_command_line()
    parser = argparse.ArgumentParser()
    ovs.vlog.add_args(parser)
    args = parser.parse_args()
    ovs.vlog.handle_args(args)

    app_log.debug("Creating OVSDB API Application!")
    app = OvsdbApiApplication(settings)

    if options.create_ssl:
        create_ssl_pki()

    HTTP_server = tornado.httpserver.HTTPServer(app)
    app_log.debug("Server listening on: [%s]:%s" % (
        options.listen, options.HTTP_port))
    HTTP_server.listen(options.HTTP_port, options.listen)

    if options.HTTPS:
        HTTPS_server = tornado.httpserver.HTTPServer(app, ssl_options={
            "certfile": SSL_CRT_FILE,
            "keyfile": SSL_PRIV_KEY_FILE})
        app_log.debug("Server listening on: [%s]:%s" % (
            options.listen, options.HTTPS_port))
        HTTPS_server.listen(options.HTTPS_port, options.listen)

    unixmgr = UnixctlManager()
    unixmgr.start()
    app_log.info("Starting server!")
    tornado.ioloop.IOLoop.instance().start()

if __name__ == "__main__":
    main()
