'use strict';
const url = require('url');
const AWS = require('aws-sdk');
const s3 = new AWS.S3({apiVersion: '2006-03-01'});
const simpleParser = require('mailparser').simpleParser;
const htmlparser2 = require('htmlparser2');
const agent = require('superagent');

const DATA_STAGING_BUCKET = `animl-data-staging-${process.env.STAGE}`;
const LINCKEAZI_RE = new RegExp(/linckeazi/, 'i');
const RIDGETEC_RE = new RegExp(/ridgetec/, 'i');

const uploadToS3 = async (imgBuffer, key, bucket=DATA_STAGING_BUCKET) => {
  console.log('Uploading to s3');
  try {
    const destparams = {
        Bucket: bucket,
        Key: key,
        Body: imgBuffer,
        ContentType: 'image'
    };
    const putResult = await s3.putObject(destparams).promise(); 
    console.log('upload successful');
    return putResult;
  } catch (error) {
      console.log(error);
      return;
  } 
};

const extractImage = {
  'LinckEazi': async (email) => {
    console.log('extracting image from LinckEazi email');
    let imgLink; 
    const parser = new htmlparser2.Parser({
      onattribute(name, value) {
        if (name === 'href') {
          imgLink = value;
        }
      },
    });
    parser.write(email.html);
    parser.end();
    const img = await agent.get(imgLink);
    return Buffer.from(img.body, 'binary');;
  },
}

const extractFilename = {
  'LinckEazi': (email) => {
    console.log('extracting filename from LinckEazi email');
    const subject = email.subject;
    const parts = subject.split('_');
    return parts.filter(part => part.includes('.jpg'))[0];
  },
  'RidgeTec': (email) => {
    // NOTE: this is temporary. I don't think this is the filename that gets
    // stored/displayed in the RidgeTec portal. 
    console.log('extracting filename from RidgeTec email');
    let filename = 'UNKNOWN_FILENAME.JPG';
    const parser = new htmlparser2.Parser({
      onattribute(name, value) {
        if (name === 'src') {
          filename = url.parse(value, true).pathname.split('/')[2];
        }
      },
    });
    parser.write(email.html);
    parser.end();
    return filename;
  },
}

const getMake = (sender) => {
  let make = 'other'
  if (LINCKEAZI_RE.test(sender)) { make = 'LinckEazi' };
  if (RIDGETEC_RE.test(sender)) { make = 'RidgeTec' };
  console.log('camera make: ', make);
  return make;
};

module.exports.relayImages = async (event) => {

  const record = event.Records[0];
  const request = {
    Bucket: record.s3.bucket.name,
    Key: record.s3.object.key,
  };

  try {
    const data = await s3.getObject(request).promise();
    const email = await simpleParser(data.Body);
    console.log('email parsed: ', email);

    // If email is from a supported camera maker
    const make = getMake(email.from.text);
    if (make === 'other') {
      throw new Error('Email is not from a supported camera make');
    }

    const filename = extractFilename[make](email);
    // const imgBuffer = await extractImage[make](email);
    // await uploadToS3(imgBuffer, filename);

    return { status: 'success' };
  }
  catch(Error) {
    console.log(Error, Error.stack);
    return Error;
  }

};
